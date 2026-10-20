/* Readable C translation of independently ROM-verified Python reconstruction.
 * ROM SHA256 26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82.
 * This is a partial logic library: no complete NES frontend, AI predicate set,
 * map, animation or save engine. Keep action names unknown where unproven. */
#include "game_recovered.h"
#include <assert.h>

uint16_t rk_experience(const RKOfficer *o) { return (uint16_t)(o->bytes[6] | o->bytes[7] << 8); }
uint16_t rk_troops(const RKOfficer *o) { return (uint16_t)(o->bytes[8] | (o->bytes[9] & 3) << 8); }
uint8_t rk_level_index(const RKOfficer *o) { return o->bytes[11] >> 4; }

/* Fixed bank $E862: reject values outside [0,bound), low nibble for bound<15. */
uint8_t rk_rng_bounded(RKRng *r, uint8_t bound) {
    assert(bound != 0); /* Actual ROM loops forever at bound 0. */
    for (;;) {
        uint8_t value = r->table[r->cursor++];
        if (bound < 15) value &= 15;
        if (value < bound) return value;
    }
}

/* PRG8 $A965: 知 thresholds, independent from display level. */
uint8_t rk_knowledge_tier(uint8_t value) {
    return value < 40 ? 1 : value < 60 ? 3 : value < 75 ? 5 : value < 85 ? 7 : 9;
}
bool rk_special_ai_gate(uint8_t knowledge, uint8_t packed) {
    return knowledge >= 92 && (packed >> 4) >= 3;
}

/* PRG12 $B7BE. Positive differences only, then additions wrap before BPL. */
int rk_strategy_threshold(const RKOfficer *a, const RKOfficer *t,
                          uint8_t distance, uint8_t phase, uint8_t environment) {
    static const uint8_t distance_adjustments[6] = {15,10,5,0,251,246};
    if (distance >= 6) return -1;
    uint8_t knowledge = a->bytes[2] > t->bytes[2] ? a->bytes[2] - t->bytes[2] : 0;
    uint8_t level = rk_level_index(a) > rk_level_index(t)
        ? (uint8_t)(2 * (rk_level_index(a) - rk_level_index(t))) : 0;
    uint8_t bonus = phase != 3 ? 10 : environment == 1 ? 10 : environment == 2 ? 20 : 5;
    uint8_t value = (uint8_t)(distance_adjustments[distance] + knowledge + level + bonus);
    if (value & 128) value = 0;
    return value < 5 ? 5 : value > 95 ? 95 : value;
}

/* PRG12 $B72B: probability gate before flipping the target's side bit. */
int rk_conversion_threshold(const RKOfficer *a, const RKOfficer *t, uint8_t distance) {
    if (distance >= 6 || t->bytes[3] >= 71) return -1;
    uint8_t base = t->bytes[3] < 31 ? 60 : t->bytes[3] < 51 ? 30 : 10;
    uint8_t level = rk_level_index(a) > rk_level_index(t)
        ? (uint8_t)(2 * (rk_level_index(a) - rk_level_index(t))) : 0;
    uint8_t quotient = (uint8_t)(a->bytes[2] + a->bytes[4]) / 10;
    unsigned first = quotient + base;
    return (uint8_t)((uint8_t)first + level + (first > 255));
}

/* Six successful-effect prefixes. These entry addresses are not action names. */
uint16_t rk_strategy_damage_amount(uint16_t entry, const RKOfficer *a, RKRng *rng) {
    uint8_t level = rk_level_index(a);
    switch (entry) {
    case 0xB070: {
        uint8_t q = (uint8_t)(a->bytes[2] * (rk_rng_bounded(rng,5)+9) / 10);
        return (uint8_t)(10*level+q)+30;
    }
    case 0xB0EB: {
        uint8_t base = (uint8_t)(level + (uint8_t)(a->bytes[1]+a->bytes[2])/10);
        return (uint8_t)(base*(rk_rng_bounded(rng,3)+5)/10);
    }
    case 0xB188: return a->bytes[1]*(rk_rng_bounded(rng,7)+14)/10;
    case 0xB1E3: return a->bytes[2]*(rk_rng_bounded(rng,7)+20)/10+level+7;
    case 0xB4C6: return rk_rng_bounded(rng,200)+150+((uint8_t)(a->bytes[1]+a->bytes[2])>>1);
    case 0xB55C: return a->bytes[2]*(rk_rng_bounded(rng,6)+30)/10;
    default: assert(!"Unrecovered effect entry"); return 0;
    }
}

/* PRG12 $B5D8..$B610 prefix; later unit-removal calls are outside this API. */
uint8_t rk_apply_health_loss(RKOfficer *t, uint8_t requested) {
    uint8_t loss = requested < t->bytes[0] ? requested : t->bytes[0];
    t->bytes[0] -= loss;
    if (!t->bytes[0]) t->bytes[11] |= 3;
    return loss;
}

/* PRG15 $D7FB: wrap sum before cap; use uncapped wrapped total for one level. */
uint8_t rk_award_experience(RKOfficer *a, uint16_t counter) {
    static const uint16_t thresholds[7] = {1000,2000,3500,5000,7500,10000,15000};
    uint16_t total = (uint16_t)(rk_experience(a) + (counter >> 1));
    uint16_t capped = total < 49999 ? total : 49999;
    a->bytes[6] = capped & 255; a->bytes[7] = capped >> 8;
    uint8_t level = rk_level_index(a), marker = 0;
    if (level < 7 && total >= thresholds[level]) {
        marker = (uint8_t)((level+1)<<4);
        a->bytes[11] = (a->bytes[11]&15) | marker;
        uint8_t war = a->bytes[1];
        a->bytes[1] = (uint8_t)(war + (war<51?6:war<71?5:war<81?4:war<90?2:0));
    }
    return marker;
}

/* PRG12 $B68B, including its real far-call award path. */
uint16_t rk_apply_troop_loss(RKOfficer *a, RKOfficer *t, uint16_t requested,
                            uint16_t *counter, uint8_t *marker) {
    assert(a != t);
    uint16_t troops = rk_troops(t), loss = requested < troops ? requested : troops;
    uint16_t remaining = troops - loss;
    t->bytes[8] = remaining & 255; t->bytes[9] = remaining >> 8;
    *counter = (uint16_t)(*counter + loss);
    *marker = rk_award_experience(a,*counter);
    return loss;
}

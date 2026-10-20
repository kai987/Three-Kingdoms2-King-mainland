#ifndef ROM_GAME_RECOVERED_H
#define ROM_GAME_RECOVERED_H
#include <stdint.h>
#include <stdbool.h>

/* Reconstructed behavior, not original source. Raw ROM records are 12 bytes.
 * Names follow UI glyphs: 体/武/知/忠/徳/経/兵. Field5/status detail is separate.
 * Do not map this structure directly over a host-endian packed C struct. */
typedef struct { uint8_t bytes[12]; } RKOfficer;
typedef struct { uint8_t table[256]; uint8_t cursor; } RKRng;

uint16_t rk_experience(const RKOfficer *officer);
uint16_t rk_troops(const RKOfficer *officer);
uint8_t rk_level_index(const RKOfficer *officer);
uint8_t rk_rng_bounded(RKRng *rng, uint8_t nonzero_bound);
uint8_t rk_knowledge_tier(uint8_t knowledge);
bool rk_special_ai_gate(uint8_t knowledge, uint8_t packed_byte11);
/* Threshold routines preserve CPU byte wrap/sign behavior. Range >=6 => -1. */
int rk_strategy_threshold(const RKOfficer *actor, const RKOfficer *target,
                          uint8_t distance, uint8_t phase_type, uint8_t environment);
int rk_conversion_threshold(const RKOfficer *actor, const RKOfficer *target, uint8_t distance);
uint16_t rk_strategy_damage_amount(uint16_t cpu_entry, const RKOfficer *actor, RKRng *rng);
uint8_t rk_apply_health_loss(RKOfficer *target, uint8_t requested_loss);
uint8_t rk_award_experience(RKOfficer *actor, uint16_t accumulated_loss);
/* Actor and target must be different records. Removal/animation is not modeled. */
uint16_t rk_apply_troop_loss(RKOfficer *actor, RKOfficer *target, uint16_t requested_loss,
                            uint16_t *accumulated_loss, uint8_t *level_marker);
#endif

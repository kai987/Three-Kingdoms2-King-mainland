// WP05 passive observer only. No emulator state is stored here.
#ifndef NST_PASSIVE_AUXILIARY_WATCH_HPP
#define NST_PASSIVE_AUXILIARY_WATCH_HPP
extern "C" void nestopia_wp05_set_provider(void (*)(const void*,unsigned,unsigned*),const void*);
extern "C" void nestopia_wp05_set_snapshot_provider(void (*)(const void*,unsigned char*));
#endif

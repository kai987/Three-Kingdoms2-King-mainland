# scene_initialization

Global setup E18B/E22F/E2E8 requests battle/ordinary attack/duel and ends at E066, not a caller RTS.

Display reset disables NMI/rendering, resets the original audio driver, clears nametables/OAM and real queues.

Raw1024-byte, marker RLE, metatile, palette,48-byte CHR and IRQ loaders retain their mapper and port ordering.

PPUSTATUS reads are explicit resumable inputs; requesting fade/rendering is not completed hardware time.

Raw evidence offsets include the16-byte iNES header. See validation.json for exact comparisons, inputs and guards.

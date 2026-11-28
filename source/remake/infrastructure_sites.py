"""Pilot sites at authored river-network ports, in original map pixels."""

# The ports are experimental facilities tied to city control. The coordinates
# and reach names are from game/config/river-network.json, not historical claims.
SITES = {
    'wharf-fuling': ('fuling', 'yangtze:fuling', (491, 578), '涪陵河埠', '涪陵河港'),
    'wharf-badong': ('badong', 'yangtze:badong', (568, 507), '巴東河埠', '巴東河港'),
    'wharf-cangwu': ('cangwu', 'pearl:cangwu', (611, 793), '蒼梧河埠', '蒼梧河港'),
    'wharf-nanhai': ('nanhai', 'pearl:nanhai', (737, 796), '南海河埠', '南海河港'),
    'wharf-wei': ('wei', 'yellow:wei', (811, 278), '魏河埠', '魏河港'),
    'wharf-dongjun': ('dongjun', 'yellow:dongjun', (825, 273), '東郡河埠', '東郡河港'),
}
CORRIDORS = {
    'fuling:badong:river': ('wharf-fuling', 'wharf-badong'),
    'cangwu:nanhai:river': ('wharf-cangwu', 'wharf-nanhai'),
    'wei:dongjun:river': ('wharf-wei', 'wharf-dongjun'),
}

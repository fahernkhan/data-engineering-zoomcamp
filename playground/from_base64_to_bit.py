import base64

data_b64 = "CiQA37vxDKw5CNNmMRSjX2i3OfHmH9iSc70c6ublnbUaQNtVRlUStQEAE/0jGULqnKhbnd5iHtyYfQeVqTawN2WAt1ud3GBlAfWq4x1mhzZMhkoiz2e/ZKaAnL8Rb6gmd2l2rArBAhLZNiPOTYdSyFJDdahUeIYvi/8vpF0KQP3u9RZ92zxb7dgB/WERp4hXpDIgc6KFMCic22mrh0nXHZVIJ2vImb+L2BnjwUB3C8VCAkiWFr6PNYYcIM2s9UtJze5Tf4vGDLl1Cv41qXRns23ruGL7o+djQwI0W4oK"

# 1. Decode base64 ke bytes
data_bytes = base64.b64decode(data_b64)

# 2. Ubah ke format hex \xHH
hex_format = "".join([f"\\x{b:02x}" for b in data_bytes])

print(f"B'{hex_format}'")
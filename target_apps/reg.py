def process_str(s):
    return "CW-" + str(ord(s[0]) * 0x29 * 2) + "-CRACKED"

print(process_str("123456789"))  # 3480

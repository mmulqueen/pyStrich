"""Generate test images for code39 barcode encoder"""
if __name__ == "__main__":
    from pystrich.code39 import Code39Encoder
    from pystrich.code39.test_code39 import test_strings

    for index, text in enumerate(test_strings):
        enc = Code39Encoder(text)
        enc.save(f"pystrich/code39/test_img/{index + 1}.png")

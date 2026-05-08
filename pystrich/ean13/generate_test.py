"""Generate test images for EAN13 barcode encoder"""
if __name__ == "__main__":
    from pystrich.ean13 import EAN13Encoder
    from pystrich.ean13.test_ean13 import EAN13Test


    for index, string in enumerate(EAN13Test.test_strings):
        enc = EAN13Encoder(string)
        enc.save(f"pystrich/ean13/test_img/{index + 1}.png")

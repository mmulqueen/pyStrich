Choosing the right symbology
============================

This is meant to be an accessible introduction to the different kinds of
barcodes that can be used and some rules of thumb for picking the right
one. This article probably isn't for you if you're planning a mass
rollout, but I hope it'll be a useful starting point. Similarly, if
you're generating a label or document that's been standardised, the
decision may already have been made for you.

Everyone gets QR codes
----------------------

QR codes are the most famous 2D barcode, everyone has heard of a QR code
and probably scanned many of them. They have a distinctive appearance,
even when stylised. They're supported by every modern smartphone without
installing anything. If you want members of the public to scan it, QR
codes should be your default choice. QR codes are likely to become even
more popular over the next couple of years as GS1 Digital Link QR codes
start to take over from classic 1D EAN barcodes in the shops.

The downside of QR codes is that they're relatively bulky as 2D barcodes
go and while they're somewhat damage tolerant, it depends on where that
damage is.

.. only:: not text

   .. figure:: examples/qrcode-example.svg
      :alt: QR Code example.

      QR Code

But consider Data Matrix and Aztec
----------------------------------

If you have more control over who/how you scan, Data Matrix and Aztec
codes are well worth considering. They can be denser for typical
payloads. Aztec codes are especially suited to environments where they
might get damaged because the locator is in the middle, which is less
exposed to edge wear than the corner locators on a QR code or the
border locator on a Data Matrix symbol. Data Matrix is well established
for part marking and its simple
structure lends itself to many different physical marking methods like
engraving, dot peening and laser. While not as well-known to the general
public, Data Matrix barcodes are everywhere -- just looking around my
home I see them on the packaging for medicines, Amazon deliveries,
letters from banks -- and it's even more popular in industrial and
healthcare settings. I see Aztec codes far less in the wild, I've
spotted them on brewery kegs, rail tickets, airline boarding passes and
the Tesco Clubcard.

The central locator on an Aztec code bears some similarity to the
locators on QR codes, which may be a helpful affordance to users
understanding how to scan it. This may not always be an advantage,
because it may cause frustration if someone tries to scan an Aztec code
with their phone's built-in camera app and it doesn't work. The
iOS/Android camera app supports QR codes and my Samsung Android phone at
least supports Data Matrix too. If the symbol is being scanned in your
own app, this isn't a problem, Google's ML Kit and Apple's VisionKit
easily support any of these.

.. only:: not text

   .. list-table::
      :widths: 50 50
      :header-rows: 1

      * - Data Matrix
        - Aztec Code
      * - .. image:: examples/datamatrix-example.svg
             :alt: Data Matrix example.
        - .. image:: examples/aztec-example.svg
             :alt: Aztec Code example.

Anything else needs a good reason
---------------------------------

I haven't mentioned PDF417 yet, and that's because I think the only good
reason to use them in 2026 is if you have to. They take up a lot of
physical space and in my experience, scanners struggle with larger
PDF417 symbols too. They made sense in a world of linear scanners, which
have largely died out as other 2D barcodes and on-screen scanning has
been popularised. I do still come across them -- Eurostar boarding passes
spring to mind.

There are other kinds of 2D barcodes -- but they're even more niche and
if you needed to use them, you'd already know about them.

Should you use a 1D barcode? Again, if you needed to, you'd already know.
Chances are it would be an EAN-13 if it's a consumer product. Code 128
remains popular in industrial settings. But if you have a choice, go 2D
instead.

.. only:: not text

   .. list-table::
      :widths: 33 33 33
      :header-rows: 1

      * - PDF417
        - Code 128
        - EAN-13
      * - .. image:: examples/pdf417-example.svg
             :alt: PDF417 example.
        - .. image:: examples/code128-example.svg
             :alt: Code 128 example.
        - .. image:: examples/ean13-example.svg
             :alt: EAN-13 example.

.. seealso::

   :doc:`printing` once you've chosen -- how to size a symbol so it scans
   reliably.

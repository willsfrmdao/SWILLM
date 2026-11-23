# SWILLM swim shop

SWILLM is a local storefront for a school project. It uses Python 3.10 or later and the standard library.

## Run the shop

On Windows, double-click `Start SWILLM.cmd` to start the shop. Keep the launcher window open. Then double-click `index.html` or open [the storefront](http://127.0.0.1:8000). You can also run `python server.py` from this folder and stop it with Ctrl+C.

Open [the order desk](http://127.0.0.1:8000/admin.html) to view orders and the owner email status.

The homepage uses the supplied pool photo in `public/images/swim-cover.jpg`. The Men, Women, Children and Unisex gear collections support product-type filtering and search. Checkout accepts a name and email, saves the demo order in `data/orders.json` and displays an order reference. The shop collects no payment.

## Swimming classes

Open [Swimming classes](http://127.0.0.1:8000/#classes) to request a 1-, 2- or 6-month programme with a dedicated teacher. Swimmers can request a male or female teacher and receive a reference when the server saves their request. The [class registration desk](http://127.0.0.1:8000/admin.html#class-registrations) shows the contact email, programme and teacher preference for follow-up. Requests are saved locally in `data/class-registrations.json` and await teacher and schedule confirmation.

## Enable order emails

The server queues a message for **willchisom341@gmail.com** when it saves an order. The email includes the order reference, customer contact, chosen sizes and colours, quantities and subtotal.

1. Create a Gmail App Password for the sending account. Google requires 2-Step Verification. [Google’s App Password instructions](https://support.google.com/accounts/answer/185833)
2. Stop the shop server. In PowerShell 7, enter the App Password when prompted and then restart the server in that same window.

   ```powershell
   $env:SWILLM_SMTP_PASSWORD = Read-Host -MaskInput 'Gmail App Password'
   & '.\Start SWILLM.cmd'
   ```

3. Place a demo order and check the inbox and the order desk. The order desk shows `sent` after Gmail accepts the message for delivery.

The sender defaults to **willchisom341@gmail.com**. To send from a different Gmail account, set `SWILLM_SMTP_USER` to its address before starting the server and use that account’s App Password. Keep the password in your server environment. Orders saved while email is unconfigured stay queued. The server sends queued notifications when it starts with credentials and retries transient failures while it runs. The storefront and order desk bind to the local computer.

## Product photo credits

The catalog uses online reference photos to illustrate the item types. Product names, prices, sizes and colours are demo catalog details. For commercial use, use your own inventory photos or confirm reuse rights for the images.

- [AquaForm Goggles — SHVETS production, Pexels](https://www.pexels.com/photo/close-up-photo-of-swimming-goggles-8028456/)
- [Sprint Training Fins — SHVETS production, Pexels](https://www.pexels.com/photo/close-up-shot-of-swimfins-near-a-swimming-pool-8028423/)
- [Tidal Mirror Goggles](https://us.speedo.com/speed-socket-2.0-mirrored-goggle/13248569.html)
- [Open-Water Racerback Suit](https://us.speedo.com/women-s-colorblock-splice-2.0-one-piece-black-turquoise/17468468.html)
- [Flow Training Suit](https://ernies.ca/products/endurnce-plus-solid-super-pro-one-piece)
- [Silicone Swim Cap](https://www.swimoutlet.com/products/speedo-elastomeric-solid-silicone-swim-cap-8114602)
- [Wave Print Swim Cap](https://www.swimoutlet.com/products/sporti-sonar-waves-silicone-swim-cap-8212931)
- [Long-Hair Comfort Cap](https://www.sportsdirect.com.my/speedo-long-hair-swim-cap-883002)
- [Open-Water Long Fins](https://dipndive.com/products/cressi-agua-full-foot-fins)
- [SoftSeal Ear Plugs](https://supersports.com.vn/products/bit-tai-boi-nguoi-lon-zoggs-ear-plugs-aqua-plugz-300659)
- [AquaFit Ear Plug Set](https://www.decathlonpro.fr/art-bouchons-d-oreilles-natation-thermoplastique-malleable-bleus-et-roses-id-865081.html)
- [Current Swim Trunks](https://www.lolelife.com/products/cove-swim-trunks-lsm0134)
- [Reef Stripe Swim Trunks](https://www.marlowandquinn.com/products/mens-striped-drawstring-swimming-trunks)
- [Junior Splash Trunks](https://www.decathlon.de/kinder/badehosen)
- [Reef Explorer Swim Set](https://www.walmart.com/ip/15960203057)
- [Little Wave Goggles](https://www.fastlegs.co.uk/speedo-futura-biofuse-junior-goggle)
- [Poolside Gear Bag](https://en-sa.sssports.com/speedo-equipment-mesh-bag/5051746650276.html)
- [Lane Training Jammer](https://www.sportsdirect.com/speedo-end-jam-sn00-352083)
- [Stride Training Legsuit](https://www.dhbsport.com/products/dhb-hydron-womens-legsuit)
- [Shark Junior Swim Cap](https://mondo.co.nz/products/zoggs-swim-cap-junior-blue-shark)

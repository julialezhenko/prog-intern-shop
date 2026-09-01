# Image sources

All storefront photography is free-to-use imagery from [Unsplash](https://unsplash.com) (Unsplash licence: free for
commercial and non-commercial use, no attribution required — credits below are a courtesy). Only `photo-…` ids are
used; no Unsplash+ assets. Images are hot-linked through Unsplash's image CDN with size parameters
(`?auto=format&fit=crop&w=…&q=75`), so nothing large is stored in the repository and every `<img>` is resized for its
slot by the `img` template filter (`catalog/templatetags/storefront_extras.py`). Uploaded files (`ProductImage.image`,
`Category.image`) take precedence over URLs, so a real deployment can replace any of them from the admin.

| Used for | Unsplash photo id |
|---|---|
| Home hero (pour-over) | photo-1500557515707-69f05f65df7d |
| Promo band (bean scoop) | photo-1690983326555-8b8e27843a32 |
| Subscription band / category | photo-1748895177768-b4a54b9c2954 |
| Roastery editorial | photo-1511537190424-bbbab87ac5eb |
| About page roaster / brew bar | photo-1741994043738-393513f7bf52, photo-1619860703338-9c70a1af6a63 |
| Category tiles | photo-1545665225-b23b99e4d45e, photo-1649882453801-d5f84502c3f0, photo-1508088405209-fbd63b6a4f50, photo-1643427517196-7822b972517f, photo-1621745147794-843ab24c3b05 |
| Coffee bags (product primaries) | photo-1695245503558-5cdb37f49092, photo-1669296667524-906d519cbe3e, photo-1661669037570-72efa689b68d, photo-1615380547241-75c51aad004e, photo-1712402832925-d41c446883d3, photo-1661669037616-4e78ad5dfbfb, photo-1630595478342-5b257b95f783, photo-1565273975921-c884f2b703df |
| Beans / cups (product secondaries) | photo-1692299116305-762729f2e9d5, photo-1442550528053-c431ecb55509, photo-1513530176992-0cf39c4cbed4, photo-1509785307050-d4066910ec1e, photo-1536227661368-deef57acf708, photo-1607681034540-2c46cc71896d, photo-1580933073521-dc49ac0d4e6a, photo-1666873903780-396269c73a54, photo-1447933601403-0c6688de566e, photo-1497935586351-b67a49e012bf |
| Brewing (V60, Chemex, drip bags) | photo-1517224187585-e3016a5fddc8, photo-1748894851733-be6747a9c061, photo-1530346460498-48afc564f57a, photo-1545665613-29394cee622b, photo-1597341510440-5b82f96e6dcf, photo-1643427517196-7822b972517f, photo-1749137997054-d556a40051aa, photo-1770579673855-ab18aabe71a2, photo-1516510516159-156347b3cf2b, photo-1676600475896-dbf8ddd44f1d, photo-1504469089401-14f795f6ddee |
| Espresso | photo-1510591509098-f4fdc6d0ff04, photo-1627902511858-6ad7e004fd35, photo-1601390483714-955fd3066695, photo-1641759677597-15b2422bc0e8, photo-1558416165-5fb04b79b0e7, photo-1610889556528-9a770e32642f, photo-1553742198-6eea5ac42a24, photo-1508088405209-fbd63b6a4f50, photo-1574377727482-e82003fd3609, photo-1655933143757-cb624d6ba031 |
| Equipment (grinders, kettles, servers, mugs) | photo-1573068012813-e4c7558d8765, photo-1573066380308-24ff4c273dbc, photo-1611829371108-544962e333af, photo-1461988279488-1dac181a78f9, photo-1629248990514-c350da4e7bc9, photo-1621745147794-843ab24c3b05, photo-1768674150917-55b1ddf46a02, photo-1650940925927-f4a30c930a4d, photo-1636903696124-649c068a69c9, photo-1609213766164-61ce4ab825f0, photo-1495100497150-fe209c585f50, photo-1552010266-6458fda4d692, photo-1563696629964-8c3ce077cf3e |
| Origin stories (farms, cherries, landscapes) | photo-1515694590185-73647ba02c10, photo-1633437805600-2c58bf56663c, photo-1663125365404-e274869480f6, photo-1647220577886-6a5faaa7c141, photo-1629008642899-178df6fc5f2f, photo-1472495010058-65576a9959e4, photo-1626402679707-b248aa61e5ff, photo-1701735513192-bc7248978c51, photo-1677125671399-65852c6dfb05, photo-1741993677051-29ffdc7c6830, photo-1613399421011-1e634fa4dacc |

The mapping of ids to products lives in `catalog/demo_catalog.py` (`PRODUCTS[*]["images"]`, `story_image`) and
`CATEGORIES`. The wordmark, bean mark and favicon (`static/img/favicon.svg`) are original inline SVGs.

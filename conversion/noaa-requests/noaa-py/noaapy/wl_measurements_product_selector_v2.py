def wl_measurements_product_selector_v2(d_struct, prod):
    """
    Given the station's list of available WL products and a product name,
    return:
        flag2 : 0 if station has the product, 1 otherwise
        flag1 : short code ('m', '1', '6', '6p', 'hilo')
        indx  : list of indices where this product appears
    """

    # Mapping of product names → short flags
    product_flags = {
        "Verified Monthly Mean Water Level": "m",
        "Verified Hourly Height Water Level": "1",
        "Verified 6-Minute Water Level": "6",
        "Preliminary 6-Minute Water Level": "6p",
        "Verified High/Low Water Level": "hilo",
    }

    if prod not in product_flags:
        raise ValueError(f"Product not recognized: {prod!r}")

    flag1 = product_flags[prod]

    print(d_struct)
    given = d_struct["WL_products"]

    # Find all indexes where station supports this exact product
    indx = [i for i, g in enumerate(given) if g == prod]
    # Flag2 indicates presence (MATLAB: flag2 = 1 if not found)
    flag2 = 0 if indx else 1

    return flag2, flag1, indx

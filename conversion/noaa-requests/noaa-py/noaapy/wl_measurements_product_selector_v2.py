from typing import Tuple

from noaapy import globals


def measurements_product_flags(d_struct, prod) -> Tuple[bool, bool, int]:
    """
    Given the station's list of available WL products and a product name,
    return:
        flag2 : 0 if station has the product, 1 otherwise
        flag1 : short code ('m', '1', '6', '6p', 'hilo')
        indx  : list of indices where this product appears
    """
    # Mapping of product names → short flags
    if prod not in globals.PRODUCT_FLAGS:
        raise ValueError(f"Product not recognized: {prod}")
    flag1: bool = globals.PRODUCT_FLAGS[prod]
    given = d_struct["WL_products"]
    # Find all indexes where station supports this exact product
    idxs = [i for i, g in enumerate(given) if g == prod]
    # Flag2 indicates presence (MATLAB: flag2 = 1 if not found)
    isProductAvailable: bool = False if idxs else True
    return isProductAvailable, flag1, idxs

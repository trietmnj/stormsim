from typing import Tuple

from noaapy import globals
import noaapy


def measurements_product_flags(prod) -> Tuple[bool, bool, int]:
    """
    Given the station's list of available WL products and a product name,
    return:
        is_product_available : 0 if station has the product, 1 otherwise
        interval_param : short code ('m', '1', '6', '6p', 'hilo')
        idxs  : list of indices where this product appears
    """
    if prod not in noaapy.globals.INTERVAL_NAME_TO_PARAM:
        raise ValueError(f"Product not recognized: {prod}")

    interval_param: str = noaapy.globals.INTERVAL_NAME_TO_PARAM[prod]
    given = globals.INTERVAL_NAME_TO_PARAM
    idxs = [i for i, g in enumerate(given) if g == prod]
    is_product_available: bool = False if idxs else True
    return is_product_available, interval_param, idxs

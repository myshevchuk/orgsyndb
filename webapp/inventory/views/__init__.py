"""The inventory's lists, pages and forms."""

from inventory.views.batches import (batch_detail, batch_edit, batch_list,
                                     batch_new, batch_page)
from inventory.views.bulk import bulk_detail, bulk_list
from inventory.views.categories import (chemical_detail, chemical_list,
                                        intermediate_detail,
                                        intermediate_list)
from inventory.views.common import LIST
from inventory.views.items import (item_consumption, item_correct,
                                   item_detail, item_edit, item_fill,
                                   item_list, item_new, item_page,
                                   movement_reverse)
from inventory.views.notes import (note_detail, note_edit, note_list,
                                   note_new, note_page, note_reverse)
from inventory.views.vessels import (vessel_correct, vessel_detail,
                                     vessel_edit, vessel_list,
                                     vessel_movement_reverse, vessel_new,
                                     vessel_page, vessel_transfer,
                                     vessel_withdraw)

__all__ = [
    "LIST",
    "batch_detail",
    "batch_edit",
    "batch_list",
    "batch_new",
    "batch_page",
    "bulk_detail",
    "bulk_list",
    "chemical_detail",
    "chemical_list",
    "intermediate_detail",
    "intermediate_list",
    "item_consumption",
    "item_correct",
    "item_detail",
    "item_edit",
    "item_fill",
    "item_list",
    "item_new",
    "item_page",
    "movement_reverse",
    "note_detail",
    "note_edit",
    "note_list",
    "note_new",
    "note_page",
    "note_reverse",
    "vessel_correct",
    "vessel_detail",
    "vessel_edit",
    "vessel_list",
    "vessel_movement_reverse",
    "vessel_new",
    "vessel_page",
    "vessel_transfer",
    "vessel_withdraw",
]

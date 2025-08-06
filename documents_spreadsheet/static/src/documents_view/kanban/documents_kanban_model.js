/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { DocumentsKanbanRecord } from "@documents/views/kanban/documents_kanban_model";

import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";

patch(DocumentsKanbanRecord.prototype, {
    /**
     * @override
     */
    isViewable() {
        return (
            this.data.handler === "spreadsheet" ||
            XLSX_MIME_TYPES.includes(this.data.mimetype) ||
            super.isViewable(...arguments)
        );
    },

    /**
     * @override
     * @param {MouseEvent} ev
     */
    async onClickPreview(ev) {
        if (this.data.mimetype === "application/vnd.ms-excel") {
            this.model.env.services.notification.add(
                _t("Only XLSX files can be opened with Odoo Spreadsheet"),
                { type: "warning" }
            );
            return;
        }
        super.onClickPreview(...arguments);
    },
});

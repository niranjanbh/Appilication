// Alpine.js component powering admin multi-select bulk actions.
//
// The x-data lives on a parent element that HTMX never swaps (the .table-wrap
// wrapper), so `selected` survives tbody replacements from filtering and
// pagination. Each row checkbox binds :checked to membership in `selected`, so
// when HTMX re-renders the tbody the checkbox state is reconstructed from the
// retained selection.
//
// After every HTMX swap we prune ids that are no longer present in the DOM —
// otherwise filtering to a different page could submit ids the admin can no
// longer see.
function bulkSelect() {
  return {
    selected: [],

    init() {
      // Prune selections that left the DOM after an HTMX tbody swap.
      this.$el.addEventListener('htmx:afterSwap', () => {
        const present = new Set(
          [...this.$el.querySelectorAll('tbody input[type="checkbox"][data-bulk-id]')]
            .map((cb) => cb.getAttribute('data-bulk-id'))
        );
        this.selected = this.selected.filter((id) => present.has(id));
      });
    },

    isChecked(id) {
      return this.selected.includes(id);
    },

    get rowCount() {
      return this.$el.querySelectorAll('tbody input[type="checkbox"][data-bulk-id]').length;
    },

    get allSelected() {
      const n = this.rowCount;
      return n > 0 && this.selected.length === n;
    },

    toggle(id) {
      const idx = this.selected.indexOf(id);
      if (idx === -1) this.selected.push(id);
      else this.selected.splice(idx, 1);
    },

    toggleAll(event) {
      if (event.target.checked) {
        this.selected = [
          ...this.$el.querySelectorAll('tbody input[type="checkbox"][data-bulk-id]'),
        ].map((cb) => cb.getAttribute('data-bulk-id'));
      } else {
        this.selected = [];
      }
    },

    clearAll() {
      this.selected = [];
    },
  };
}

window.bulkSelect = bulkSelect;

/**
 * UITOP list pager — Alpine helpers + shared UI behaviour.
 * Usage in Alpine components:
 *   return Object.assign(UITOP.createPager(10), { ... hub ... });
 *   x-for="row in pagedItems(filtered)"
 *   then include alpine pager markup with itemsExpr "filtered"
 */
(function () {
  "use strict";

  var UITOP = (window.UITOP = window.UITOP || {});

  function asList(items) {
    if (!items) return [];
    if (Array.isArray(items)) return items;
    return [];
  }

  UITOP.createPager = function (perPage) {
    perPage = perPage || 10;
    return {
      page: 1,
      perPage: perPage,
      pagedItems: function (items) {
        items = asList(items);
        var pages = Math.max(1, Math.ceil(items.length / this.perPage) || 1);
        if (this.page > pages) this.page = pages;
        if (this.page < 1) this.page = 1;
        var start = (this.page - 1) * this.perPage;
        return items.slice(start, start + this.perPage);
      },
      uitopTotalPages: function (items) {
        items = asList(items);
        if (!items.length) return 1;
        return Math.max(1, Math.ceil(items.length / this.perPage));
      },
      uitopPageNumbers: function (items) {
        var pages = this.uitopTotalPages(items);
        var cur = this.page;
        var start = Math.max(1, cur - 2);
        var end = Math.min(pages, start + 4);
        start = Math.max(1, end - 4);
        var nums = [];
        for (var i = start; i <= end; i++) nums.push(i);
        return nums;
      },
      uitopFrom: function (items) {
        items = asList(items);
        if (!items.length) return 0;
        return (this.page - 1) * this.perPage + 1;
      },
      uitopTo: function (items) {
        items = asList(items);
        if (!items.length) return 0;
        return Math.min(items.length, this.page * this.perPage);
      },
      goPage: function (n, items) {
        var pages = this.uitopTotalPages(items);
        this.page = Math.max(1, Math.min(Number(n) || 1, pages));
      },
      resetPage: function () {
        this.page = 1;
      },
      /** Call from Alpine init(): this.watchPagerReset(['q','statusFilter']) */
      watchPagerReset: function (keys) {
        var self = this;
        (keys || ["q"]).forEach(function (key) {
          if (typeof self.$watch === "function") {
            self.$watch(key, function () {
              self.page = 1;
            });
          }
        });
      },
    };
  };
})();

/* Saved rolls for this browser. A published grok.me app keeps the same
   row shape in its database so everyone with the link sees one list. */
(function () {
  const KEY = "d20-kupo-log";
  const MAX_AGE = 3 * 24 * 60 * 60 * 1000;
  const MAX_NAME = 40;

  function load() {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(raw) ? raw : [];
    } catch (e) {
      return [];
    }
  }

  function fresh(rows) {
    const cut = Date.now() - MAX_AGE;
    return rows.filter(function (row) {
      const t = row && Date.parse(row.rolledAt);
      return typeof t === "number" && t >= cut;
    });
  }

  function write(rows) {
    try {
      localStorage.setItem(KEY, JSON.stringify(rows));
    } catch (e) {}
  }

  function facesOf(dice) {
    if (!Array.isArray(dice)) return [];
    return dice
      .map(function (n) { return n | 0; })
      .filter(function (n) { return n >= 1 && n <= 20; });
  }

  function rollText(row) {
    const dice = facesOf(row.dice);
    if (dice.length >= 2) return dice[0] + " + " + dice[1] + " = " + (dice[0] + dice[1]);
    if (dice.length === 1) return String(dice[0]);
    return "";
  }

  function formatCentral(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Chicago",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    }).format(d);
  }

  window.RollLog = {
    maxName: MAX_NAME,
    list: function () {
      const rows = fresh(load());
      write(rows);
      rows.sort(function (a, b) { return Date.parse(b.rolledAt) - Date.parse(a.rolledAt); });
      return rows;
    },
    save: function (name, dice, rolledAt) {
      const trimmed = String(name || "").replace(/\s+/g, " ").trim().slice(0, MAX_NAME);
      const faces = facesOf(dice);
      if (!trimmed || !faces.length) return null;
      const when = rolledAt || new Date().toISOString();
      if (Number.isNaN(Date.parse(when))) return null;
      const row = {
        id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
        name: trimmed,
        rolledAt: new Date(when).toISOString(),
        dice: faces.slice(0, 2),
      };
      const rows = fresh(load());
      rows.push(row);
      write(rows);
      return row;
    },
    label: function (row) {
      return row.name + " — " + rollText(row) + " — " + formatCentral(row.rolledAt);
    },
  };
})();

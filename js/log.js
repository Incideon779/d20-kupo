/* Shared rolls live in saves/rolls.json when this page is served by tools/serve.py.
   Any other copy keeps the list in this browser only. */
(function () {
  const KEY = "d20-kupo-log";
  const MAX_AGE = 3 * 24 * 60 * 60 * 1000;
  const MAX_NAME = 40;
  let mode = "local";

  const ready = fetch("/api/rolls", { headers: { Accept: "application/json" } })
    .then(function (res) {
      if (!res.ok) return null;
      return res.json();
    })
    .then(function (body) {
      if (body && Array.isArray(body.rows)) mode = "server";
    })
    .catch(function () {});

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

  function sortNewest(rows) {
    return rows.slice().sort(function (a, b) {
      return Date.parse(b.rolledAt) - Date.parse(a.rolledAt);
    });
  }

  window.RollLog = {
    maxName: MAX_NAME,
    list: function () {
      return ready.then(function () {
        if (mode !== "server") return sortNewest(fresh(load()));
        return fetch("/api/rolls").then(function (res) {
          if (!res.ok) return [];
          return res.json();
        }).then(function (body) {
          return sortNewest((body && body.rows) || []);
        });
      });
    },
    save: function (name, dice) {
      const trimmed = String(name || "").replace(/\s+/g, " ").trim().slice(0, MAX_NAME);
      const faces = facesOf(dice).slice(0, 2);
      if (!trimmed || !faces.length) return Promise.resolve(null);
      return ready.then(function () {
        if (mode !== "server") {
          const row = {
            id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
            name: trimmed,
            rolledAt: new Date().toISOString(),
            dice: faces,
          };
          const rows = fresh(load());
          rows.push(row);
          write(rows);
          return row;
        }
        return fetch("/api/rolls", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: trimmed, dice: faces }),
        }).then(function (res) {
          if (!res.ok) return null;
          return res.json();
        }).then(function (body) {
          return body && body.row ? body.row : null;
        });
      });
    },
    label: function (row) {
      return row.name + " — " + rollText(row) + " — " + formatCentral(row.rolledAt);
    },
  };
})();

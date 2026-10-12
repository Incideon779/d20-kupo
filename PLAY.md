# d20

One or two dice on a table. Click a die and it rolls. With two dice, that one click rolls both. A natural 20 cheers the mog in the corner. A natural 1 makes him sad. If either die of a pair is a 20, he cheers. If either is a 1 and neither is a 20, he is sad.

The page does not call a model and does not ask for an account. A finished roll can be saved under a name. On this preview the list stays in this browser. A published grok.me app keeps one shared list in the database Grok gives that app.

## Open it

```bash
cd /home/providence779/ani-online/d20-kupo
python3 tools/serve.py
```

Then open http://127.0.0.1:8099/

That server keeps one shared list in `saves/rolls.json` on this machine. Anyone who opens the page through it, including through the Cloudflare hostname pointed at port 8099, sees the same names. The file is not in git. Rows older than three days are removed when the list is opened or a roll is saved. The computer has to be on. A page opened any other way keeps a private list in that browser only.

**One**, **Two**, and **Log** sit at the top. One and Two choose how many dice are on the table. Click a die to roll. With two dice, either die starts both. A click during a tumble does nothing. The big number under the table is the face that landed up. With two dice, the sum appears once both have stopped.

About two and a half seconds after the roll stops, a small card asks for a name. The name is required. The time is added for you, in US Central time (CST in winter, CDT in summer). Close throws that roll away. Save keeps the name, the faces, the total when there are two dice, and that time. **Log** opens the list, newest first. Anything older than three days is dropped when the list is opened or a roll is saved. On this preview that cleanup uses this browser's clock, and another person does not see your rows. Switching One or Two clears the table and does not save.

Each face is a fair 1–20 (`crypto.getRandomValues`, rejection sampling so the leftover values are not biased). 6 and 9 have an underline on the die so they stay distinct. The face on top is the same number as the readout. If those ever disagree, a line appears under the number.

The mog stays in the corner and does not take clicks. He goes back to idle on any roll that is not a 1 or a 20.

## Publish on grok.com, then post on X

This folder is the roller. grok.com does not upload this folder. Build on grok.com makes its own page from a prompt, then the publish sheet gives you a grok.me link. Anyone with the link can open it. Post that link on X for the group.

1. Open https://grok.com and start a Build (the build / publish sheet, not a normal chat reply).
2. Paste the spec below.
3. When the preview rolls a die, looks like the description, and a 20 cheers the character, open Publish.
4. Choose a link anyone can open, or public, so the group can use it.
5. Copy the grok.me URL and post it on X.

The shared log lives in that published app. grok.me can store it: Build apps get a database, and the spec below tells Build to use it. Players still do not make accounts. Preview rows inside the Build chat disappear when the preview restarts. The list that the group sees is the one on the published app, and the app deletes rows older than three days using the server clock.

This folder is not that database. A static host serves the page and leaves each browser with its own list. Use a separate always-on store only if the page people open has to be this exact folder. grok.com will not attach its database to a folder you host yourself.

### Spec to paste

```
A single web page, no account, no sound.

Dark walnut table, full window. At the top center, three pill buttons: ONE, TWO, and LOG. ONE is selected at the start. ONE shows one die. TWO shows two dice, side by side, not overlapping.

The die is a red and gold icosahedron (20 triangular faces), pearl numerals, silver edges, sitting on the table. The face on top is readable. Clicking a die rolls it: it hops, tumbles, and lands with a fair random face on top, 1 through 20. With TWO selected, one click rolls both dice, each with its own fair number. A click while a die is still tumbling does nothing. The big number under the die matches the top face. 20 is gold. 1 is muted. With two dice, show both numbers with a plus between them, and the total underneath, only after both have stopped.

About two and a half seconds after the roll has stopped, show a small card: the roll, a name field, Save, and Close. Name is the only typed field, required, trimmed, at most 40 characters. The time is automatic, stored as an absolute instant and shown in US Central time (America/Chicago). Close discards the roll. Save writes one shared row that anyone with the link can read: name, time, the face or both faces, and the total when there were two dice. Keep those rows in the app database (the database Build provisions for the published app). Do not use browser-only storage for the shared list. When the log is read or a row is saved, delete rows older than three days using the server clock. LOG opens that list, newest first, and closes again. No login, no edit, no per-person delete.

A small portrait sits in the top-left corner and never blocks clicks. He is a white cat-like mog with a red pom-pom, red patterned shirt, red shorts, a whistle, and a cigarette. He is idle most of the time. He cheers on a natural 20 and looks sad on a natural 1. On a pair, he cheers if either die is 20, and he is sad if either is 1 and neither is 20. Any other result returns him to idle.

6 and 9 on the die have an underline so they cannot be confused. No other dice, no chat, no login.
```

## Checks

These open a settled die without clicking. They are for looking, not part of the table.

- `?settle=20` natural 20, mog cheers
- `?settle=1` natural 1, mog is sad
- `?settle=6` and `?settle=9` underlined, and not the same digit flipped
- `?dice=2&settle=20,8` two dice, total 28

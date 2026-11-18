// Purogé Label reservations: receives the form on puroge.com and adds a row to the
// "Purogé Label — Reservations" Google Sheet. Paste into Extensions → Apps Script in that sheet,
// then Deploy → New deployment → Web app (Execute as: Me, Who has access: Anyone).
function doPost(e) {
  var p = (e && e.parameter) || {};
  if (p.website) return ContentService.createTextOutput("ok"); // spam trap
  var email = String(p.email || "").trim();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return ContentService.createTextOutput("bad email");
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  sheet.appendRow([new Date(), String(p.name || "").slice(0, 120), email.slice(0, 200),
                   String(p.pieces || "").slice(0, 300), String(p.notes || "").slice(0, 500),
                   String(p.page || "").slice(0, 200)]);
  return ContentService.createTextOutput("ok");
}

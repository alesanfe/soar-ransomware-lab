// axe-core WCAG audit — runs inside the grafana-image-renderer sidecar.
// Usage: node axe_audit.js <url> <axe_js_path>
// Prints one JSON line: {url, violations:[{id,impact,help,nodes}], error?}
const fs = require("fs");
const puppeteer = require("puppeteer");

(async () => {
  const url = process.argv[2];
  const axePath = process.argv[3] || "/x/e2e/assets/axe.min.js";
  const out = { url };
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: process.env.CHROME_BIN || "/usr/bin/chromium-browser",
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--ignore-certificate-errors",
      ],
      timeout: 60000,
    });
    const page = await browser.newPage();
    await page.setBypassCSP(true);
    await page.setViewport({ width: 1440, height: 900 });
    const resp = await page.goto(url, {
      waitUntil: "networkidle2",
      timeout: 45000,
    });
    out.status = resp ? resp.status() : null;
    const axeSrc = fs.readFileSync(axePath, "utf8");
    await page.addScriptTag({ content: axeSrc });
    const res = await page.evaluate(async () => {
      return await axe.run(document, {
        runOnly: {
          type: "tag",
          values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
        },
        resultTypes: ["violations", "incomplete"],
      });
    });
    out.violations = res.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      help: v.help,
      nodes: v.nodes.slice(0, 8).map((n) => n.target.join(" ")),
    }));
    out.incomplete = (res.incomplete || []).length;
  } catch (e) {
    out.error = `${e.name}: ${String(e.message).slice(0, 300)}`;
  } finally {
    if (browser) await browser.close();
  }
  console.log("AXE_JSON:" + JSON.stringify(out));
})();

import { cpSync, mkdirSync } from "node:fs";
import { resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const source = fileURLToPath(new URL("../", import.meta.url));
const destination = resolve(process.argv[2] || "");
if (!process.argv[2] || destination === resolve(source) || destination.startsWith(resolve(source) + sep)) {
  throw new Error("Provide a new output directory outside website/.");
}

mkdirSync(destination, { recursive: false });
for (const name of ["index.html", "styles.css", "assets", "data", "scripts"]) {
  cpSync(resolve(source, name), resolve(destination, name), {
    recursive: true,
    filter: path => !/\.pdf$/i.test(path) && path !== fileURLToPath(import.meta.url),
  });
}

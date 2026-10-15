/** Remove the Next data cache so a resilience run starts cold. */
import { rmSync } from "node:fs";

rmSync(new URL("../.next/cache", import.meta.url), { recursive: true, force: true });

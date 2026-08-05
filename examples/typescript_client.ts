import { writeFile } from "node:fs/promises";

const baseUrl = (process.env.RENSHENG_API_BASE_URL ??
  "https://rensheng-youji-ap-454189475786.asia-east1.run.app").replace(/\/$/, "");
const apiKey = process.env.RENSHENG_API_KEY;

if (!apiKey) throw new Error("Set RENSHENG_API_KEY");

async function postJson(path: string, body: unknown): Promise<Response> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-API-Key": apiKey},
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response;
}

const birth = {
  name: "",
  birth: "1999-01-22 17:45",
  gender: "male",
  city: "泉州",
  country: "中国",
  time_basis: "true_solar_adjusted",
};

const prepared = await (await postJson("/generate", birth)).json();
console.log(prepared);

// /generate 已包含由人生有迹私有方法生成的 card_copy。
const rendered = await postJson("/render-card", birth);
await writeFile("rensheng-youji-card.png", Buffer.from(await rendered.arrayBuffer()));

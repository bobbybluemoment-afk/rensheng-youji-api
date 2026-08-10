import { writeFile } from "node:fs/promises";

const baseUrl = (process.env.RENSHENG_API_BASE_URL ??
  "https://rensheng-youji-ap-454189475786.asia-east1.run.app").replace(/\/$/, "");
const experienceCode = process.env.RENSHENG_API_KEY;

if (!experienceCode) throw new Error("Set RENSHENG_API_KEY to the one-time experience code");

async function postJson(path: string, body: unknown): Promise<Response> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-API-Key": experienceCode},
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${response.status}: ${await response.text()}`);
  return response;
}

const birth = {
  name: "",
  birth: "1999-01-22 17:45",
  gender: "male",
  city: "北京",
  country: "中国",
  time_basis: "local_civil",
};

// 准备阶段只预占体验码。
const prepared = await (await postJson("/generate", birth)).json();
console.log(prepared);

// 成功返回PNG后体验码立即失效。
const rendered = await postJson("/render-card", birth);
await writeFile("rensheng-youji-card.png", Buffer.from(await rendered.arrayBuffer()));


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

// 让调用方自己的模型根据prepared.bazi.analysis_context生成文案，并联网核对引文。
const rendered = await postJson("/render-card", {
  ...birth,
  core_mystic: "甲木生丑月，寅为根，乙劫、癸印透出；丑戌见刑，酉官坐实。",
  core_plain: [
    "你习惯在现实限制中先找到立足点，再逐步扩展。",
    "让短期成果服务长期方向，责任与资源才会成为支点。",
  ],
  main_task: "在现实压力中建立长期结构，把责任与资源变成持续生长的支点。",
  quote: "合抱之木，生于毫末；九层之台，起于累土。",
  quote_source: "《道德经》第六十四章",
});
await writeFile("rensheng-youji-card.png", Buffer.from(await rendered.arrayBuffer()));


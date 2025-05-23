// api/subscribe.js
import { writeFileSync, appendFileSync } from "fs";
import { join } from "path";

export default function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();
  const { email } = JSON.parse(req.body);
  if (!email) return res.status(400).json({ error: "Email required" });

  const file = join(process.cwd(), "subscribers.csv");
  // If file doesn’t exist, write header
  if (!fs.existsSync(file)) {
    writeFileSync(file, "email,subscribed_at\n");
  }
  appendFileSync(file, `${email},${new Date().toISOString()}\n`);
  res.status(200).json({ success: true });
}

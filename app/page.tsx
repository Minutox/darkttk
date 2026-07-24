import { getChatGPTUser } from "./chatgpt-auth";
import Dashboard from "./dashboard";
import { getRuntimeSnapshot } from "./api-client";

export const dynamic = "force-dynamic";

export default async function Home() {
  const user = await getChatGPTUser();
  const runtime = await getRuntimeSnapshot(user);

  return (
    <Dashboard
      userName={user?.displayName ?? "Tayllan"}
      userEmail={user?.email ?? "workspace@darkttk.app"}
      runtime={runtime}
    />
  );
}

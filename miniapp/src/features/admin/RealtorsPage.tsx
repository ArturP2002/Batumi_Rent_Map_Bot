import { useEffect, useState } from "react";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Realtor = {
  id: number;
  display_name: string;
  telegram_id?: number;
  rating_avg: number;
  active_listings: number;
  is_blocked: boolean;
  phone?: string;
};

export function RealtorsPage() {
  const [items, setItems] = useState<Realtor[]>([]);
  const [form, setForm] = useState({
    telegram_id: "",
    display_name: "",
    phone: "",
    whatsapp: "",
    telegram_contact: "",
  });

  async function load() {
    setItems(await api<Realtor[]>("/api/admin/realtors"));
  }

  useEffect(() => {
    void load();
  }, []);

  async function create() {
    await api("/api/admin/realtors", {
      method: "POST",
      body: JSON.stringify({
        telegram_id: Number(form.telegram_id),
        display_name: form.display_name,
        phone: form.phone || null,
        whatsapp: form.whatsapp || null,
        telegram_contact: form.telegram_contact || null,
      }),
    });
    setForm({
      telegram_id: "",
      display_name: "",
      phone: "",
      whatsapp: "",
      telegram_contact: "",
    });
    await load();
  }

  async function toggleBlock(r: Realtor) {
    await api(`/api/admin/realtors/${r.id}/block?blocked=${!r.is_blocked}`, {
      method: "POST",
    });
    await load();
  }

  return (
    <>
      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Добавить риелтора</h3>
        {(["telegram_id", "display_name", "phone", "whatsapp", "telegram_contact"] as const).map(
          (k) => (
            <div className="field" key={k}>
              <label>{k}</label>
              <input
                value={form[k]}
                onChange={(e) => setForm((p) => ({ ...p, [k]: e.target.value }))}
              />
            </div>
          ),
        )}
        <button className="btn btn-primary btn-block" onClick={() => void create()}>
          Сохранить
        </button>
      </div>
      {!items.length && <StateBox title="Риелторов пока нет" />}
      <div className="stack">
        {items.map((r) => (
          <div className="card" key={r.id}>
            <strong>{r.display_name}</strong>
            <div className="muted">
              tg:{r.telegram_id} · ★{r.rating_avg} · объектов {r.active_listings}
              {r.is_blocked ? " · BLOCKED" : ""}
            </div>
            <button className="btn btn-secondary" onClick={() => void toggleBlock(r)}>
              {r.is_blocked ? "Разблокировать" : "Заблокировать"}
            </button>
          </div>
        ))}
      </div>
    </>
  );
}

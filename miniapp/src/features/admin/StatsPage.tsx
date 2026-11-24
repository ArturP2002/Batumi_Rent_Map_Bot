import { useEffect, useState } from "react";
import { api, apiBlob } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Stats = {
  users: number; new_users: number; property_views: number; contact_clicks: number;
  inquiries: number; deals_confirmed: number; reviews_published: number;
  conversions: Record<string, number>;
  top_properties: { property_id: number; views: number }[];
  series: { day: string; property_views: number }[];
};
const dateValue = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const today = () => dateValue(new Date());
const monthAgo = () => { const d = new Date(); d.setDate(d.getDate()-30); return dateValue(d); };
const format = (v: number) => v.toLocaleString("ru-RU");
const metrics = [
  ["users", "Пользователи"], ["new_users", "Новые пользователи"],
  ["property_views", "Просмотры объектов"], ["contact_clicks", "Клики по контактам"],
  ["inquiries", "Обращения"], ["deals_confirmed", "Сделки"],
  ["reviews_published", "Отзывы"]
] as const;

export function StatsPage() {
  const [data,setData] = useState<Stats|null>(null);
  const [error,setError] = useState("");
  const [busy,setBusy] = useState(false);
  const [exportBusy,setExportBusy] = useState(false);
  const [from,setFrom] = useState(monthAgo);
  const [to,setTo] = useState(today);
  async function load() {
    if (!from || !to || from > to) { setError("Проверьте период: начальная дата не должна быть позже конечной."); return; }
    setBusy(true); setError("");
    try { const qs = new URLSearchParams({from_date:from,to_date:to}); setData(await api<Stats>(`/api/admin/stats?${qs}`)); }
    catch(e) { setError((e as Error).message || "Не удалось загрузить статистику"); }
    finally { setBusy(false); }
  }
  useEffect(()=>{void load(); /* only initial period */ // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);
  async function exportFile(ext:"csv"|"xlsx") {
    if (exportBusy || !data) return;
    setExportBusy(true); setError("");
    try {const q = new URLSearchParams({format:ext,from_date:from,to_date:to});const blob=await apiBlob(`/api/admin/stats/export?${q}`);const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=`batumi-stats-${from}-${to}.${ext}`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    catch(e){setError((e as Error).message||"Не удалось экспортировать файл");}
    finally{setExportBusy(false);}
  }
  const max = Math.max(1,...(data?.series || []).map(p=>p.property_views));
  const maxTop = Math.max(1,...(data?.top_properties || []).map(p=>p.views));
  return <>
    <header className="mba-page-heading"><div><span className="mba-overline">ДАННЫЕ ПЛАТФОРМЫ</span><h1>Аналитика<span>.</span></h1><p>Просмотры, обращения и подтверждённые сделки.</p></div></header>
    <div className="mba-stats-filters"><label>Начало периода<input type="date" value={from} max={to} onChange={e=>setFrom(e.target.value)}/></label><label>Конец периода<input type="date" value={to} min={from} onChange={e=>setTo(e.target.value)}/></label><button type="button" disabled={busy} onClick={()=>void load()}>{busy?"Загрузка…":"Применить"}</button></div>
    {error&&<div className="mba-alert" role="alert">{error}</div>}
    {!data&&busy&&<StateBox title="Считаем показатели…"/>}
    {data&&<>
      <div className="mba-metric-grid">{metrics.map(([key,label])=><div className="mba-metric" key={key}><span>{label}</span><strong>{format(data[key])}</strong></div>)}</div>
      <div className="mba-analytics-panels">
        <section className="mba-section mba-chart-section"><div className="mba-section-heading"><div><span className="mba-overline">ДИНАМИКА</span><h2>Просмотры квартир</h2></div></div>
          {data.series.length ? <div className="mba-chart" role="img" aria-label="График просмотров квартир по дням"><div className="mba-chart-bars">{data.series.map((p,i)=><div className="mba-chart-bar-wrap" key={`${p.day}-${i}`} title={`${p.day}: ${p.property_views}`}><div className="mba-chart-bar" style={{height:`${Math.max(2,p.property_views/max*100)}%`}}/></div>)}</div><div className="mba-chart-axis"><span>{data.series[0]?.day}</span><span>{data.series[data.series.length-1]?.day}</span></div></div>:<p className="mba-placeholder">Нет данных за выбранный период.</p>}
        </section>
        <section className="mba-section"><div className="mba-section-heading"><div><span className="mba-overline">РЕЗУЛЬТАТИВНОСТЬ</span><h2>Конверсии</h2></div></div><div className="mba-conversions">{Object.entries(data.conversions).length?Object.entries(data.conversions).map(([key,value])=><div className="mba-conversion" key={key}><div><span>{key.replace(/_/g, " ")}</span><strong>{(value*100).toFixed(1)}%</strong></div><div className="mba-progress"><span style={{width:`${Math.max(0,Math.min(100,value*100))}%`}}/></div></div>):<p className="mba-placeholder">Нет данных о конверсиях.</p>}</div></section>
      </div>
      <section className="mba-section"><div className="mba-section-heading"><div><span className="mba-overline">ПОПУЛЯРНОСТЬ</span><h2>Топ объявлений</h2></div></div>{data.top_properties.length ? <div className="mba-top-list">{data.top_properties.map((p,i)=><div key={p.property_id} className="mba-top-row"><span>{String(i+1).padStart(2,"0")}</span><strong>Объект №{p.property_id}</strong><div><span style={{width:`${p.views/maxTop*100}%`}}/></div><b>{format(p.views)}</b></div>)}</div>:<p className="mba-placeholder">Нет просмотров объявлений за период.</p>}</section>
      <div className="mba-export-row"><span>Выгрузить статистику за выбранный период</span><button type="button" disabled={exportBusy} onClick={()=>void exportFile("csv")}>↓ CSV</button><button type="button" disabled={exportBusy} onClick={()=>void exportFile("xlsx")}>↓ XLSX</button></div>
    </>}
  </>;
}

import { Link } from "react-router-dom";

export function HelpPage() {
  return (
    <div className="page">
      <Link className="chip" to="/map">
        ← Карта
      </Link>
      <h2>Помощь</h2>
      <div className="card">
        <p>
          Batumi Rent Map помогает найти аренду в Батуми на карте и в списке, связаться с
          риелтором и оставить отзыв после подтверждённой сделки.
        </p>
        <p className="muted">
          Онлайн-оплаты и автоматического бронирования нет. Календарь для посуточной аренды
          показывает занятость, но не блокирует даты сам по себе.
        </p>
      </div>
    </div>
  );
}

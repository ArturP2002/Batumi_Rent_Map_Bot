import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

type Props = {
  rentType: 'long_term' | 'daily';
  onRentTypeChange: (type: 'long_term' | 'daily') => void;
  onFilters: () => void;
  onMenu: () => void;
  children?: ReactNode;
};

/** Presentational replacement for the previous map-top/map-controls header. */
export function ModernBlueMapHeader({ rentType, onRentTypeChange, onFilters, onMenu, children }: Props) {
  return <header className="mb-map-header">
    <div className="mb-map-headline">
      <div className="mb-brand"><span className="mb-brand-symbol" aria-hidden="true">⌖</span><span><strong>batumi rent</strong><small>Квартиры в Батуми</small></span></div>
      <button type="button" className="mb-icon-button" aria-label="Открыть меню" onClick={onMenu}><span aria-hidden="true">☰</span></button>
    </div>
    <div className="mb-segment" role="group" aria-label="Тип аренды">
      <button type="button" aria-pressed={rentType === 'long_term'} className={rentType === 'long_term' ? 'is-selected' : ''} onClick={() => onRentTypeChange('long_term')}>Долгосрочно</button>
      <button type="button" aria-pressed={rentType === 'daily'} className={rentType === 'daily' ? 'is-selected' : ''} onClick={() => onRentTypeChange('daily')}>Посуточно</button>
    </div>
    <div className="mb-map-actions">
      <button type="button" onClick={onFilters}><span aria-hidden="true">☷</span> Фильтры</button>
      <Link to="/list"><span aria-hidden="true">≡</span> Список</Link>
    </div>
    {children}
  </header>;
}

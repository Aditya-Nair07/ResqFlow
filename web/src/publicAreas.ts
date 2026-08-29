/** Chennai demo locations → deterministic grid cells (matches backend lat/lng mapping). */

export type PublicArea = {
  label: string;
  area: string;
  lat: number;
  lng: number;
  x: number;
  y: number;
};

const GRID = 25;
const LAT_MIN = 12.9;
const LAT_MAX = 13.06;
const LON_MIN = 80.2;
const LON_MAX = 80.28;

export function latLngToGrid(lat: number, lon: number): { x: number; y: number } {
  const x = Math.round(((lon - LON_MIN) / (LON_MAX - LON_MIN)) * (GRID - 1));
  const y = Math.round(((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * (GRID - 1));
  return {
    x: Math.max(0, Math.min(GRID - 1, x)),
    y: Math.max(0, Math.min(GRID - 1, y)),
  };
}

function area(label: string, areaName: string, lat: number, lng: number): PublicArea {
  const { x, y } = latLngToGrid(lat, lng);
  return { label, area: areaName, lat, lng, x, y };
}

export const CHENNAI_AREAS: PublicArea[] = [
  area('Velachery Main Road', 'Velachery', 12.9716, 80.2421),
  area('Saidapet Bus Depot', 'Saidapet', 13.0067, 80.2206),
  area('OMR / Sholinganallur', 'OMR', 12.9352, 80.2495),
  area('Adayar Main Road', 'Adayar', 12.9411, 80.2589),
  area('Mambalam', 'Mambalam', 13.0293, 80.2348),
  area('T Nagar', 'T Nagar', 13.0339, 80.2376),
];

export function depthToSeverity(depthM: number): 'shallow' | 'rising' | 'knee_deep' | 'impassable' {
  if (depthM >= 1.0) return 'impassable';
  if (depthM >= 0.55) return 'knee_deep';
  if (depthM >= 0.3) return 'rising';
  return 'shallow';
}

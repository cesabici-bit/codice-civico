"use client";

import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { TribunalRanking } from "@/lib/types";
import { CHOROPLETH_COLORS } from "@/lib/constants";

interface Props {
  rankings: TribunalRanking[];
}

function getColor(value: number | null, min: number, max: number): string {
  if (value == null) return "#9ca3af";
  const range = max - min || 1;
  const idx = Math.min(
    Math.floor(((value - min) / range) * CHOROPLETH_COLORS.length),
    CHOROPLETH_COLORS.length - 1,
  );
  return CHOROPLETH_COLORS[idx];
}

export default function ItalyMap({ rankings }: Props) {
  const values = rankings
    .map((r) => r.metric_value)
    .filter((v): v is number => v != null);
  const min = values.length > 0 ? Math.min(...values) : 0;
  const max = values.length > 0 ? Math.max(...values) : 100;

  return (
    <MapContainer
      center={[42.0, 12.5]}
      zoom={6}
      style={{ height: "500px", width: "100%" }}
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />
      {rankings
        .filter((r) => r.lat != null && r.lon != null)
        .map((r) => (
          <CircleMarker
            key={r.name}
            center={[r.lat!, r.lon!]}
            radius={8}
            pathOptions={{
              fillColor: getColor(r.metric_value, min, max),
              fillOpacity: 0.8,
              color: "#fff",
              weight: 2,
            }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{r.name}</p>
                <p>{r.region}</p>
                <p className="mt-1">
                  {r.metric_name}: <strong>{r.metric_value?.toFixed(1) ?? "—"}</strong>
                </p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}

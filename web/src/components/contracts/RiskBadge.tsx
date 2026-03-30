import { riskColor, riskBgColor } from "@/lib/utils";

interface RiskBadgeProps {
  score: number;
}

export default function RiskBadge({ score }: RiskBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold ${riskColor(score)} ${riskBgColor(score)}`}
    >
      {Math.round(score)}
    </span>
  );
}

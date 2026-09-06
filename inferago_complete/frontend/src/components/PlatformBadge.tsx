const colors: Record<string, string> = {
  n8n:    "bg-orange-900/40 text-orange-300",
  make:   "bg-purple-900/40 text-purple-300",
  zapier: "bg-yellow-900/40 text-yellow-300",
  custom: "bg-gray-800 text-gray-300",
};

export default function PlatformBadge({ platform }: { platform: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[platform] ?? colors.custom}`}>
      {platform}
    </span>
  );
}

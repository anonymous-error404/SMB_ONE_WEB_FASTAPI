import { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  className?: string;
}

export const StatCard = ({ 
  title, 
  value, 
  change, 
  changeType = 'neutral',
  icon: Icon,
  className 
}: StatCardProps) => {
  // Determine font size based on value length
  const getValueFontSize = (val: string) => {
    const length = val.length;
    if (length <= 6) return 'text-3xl';  // Normal size for short values
    if (length <= 10) return 'text-2xl'; // Medium size
    if (length <= 15) return 'text-xl';  // Smaller for long values
    return 'text-lg';                     // Smallest for very long values
  };

  return (
    <Card className={cn('overflow-hidden transition-all hover:shadow-custom-lg', className)}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1 min-w-0">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className={cn('font-bold break-words', getValueFontSize(value))}>{value}</p>
            {change && (
              <p
                className={cn(
                  'text-sm font-medium',
                  changeType === 'positive' && 'text-success',
                  changeType === 'negative' && 'text-destructive',
                  changeType === 'neutral' && 'text-muted-foreground'
                )}
              >
                {change}
              </p>
            )}
          </div>
          <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
            <Icon className="w-6 h-6 text-white" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

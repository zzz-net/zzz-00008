import { useToast, type Toast } from '@/hooks/useToast';
import { cn } from '@/lib/utils';

const toastTypeClasses: Record<Toast['type'], string> = {
  success: 'bg-green-50 border-green-200 text-green-800',
  error: 'bg-red-50 border-red-200 text-red-800',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  info: 'bg-blue-50 border-blue-200 text-blue-800',
};

export default function ToastContainer() {
  const toasts = useToast((state) => state.toasts);
  const hideToast = useToast((state) => state.hideToast);

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg transition-all duration-300',
            toastTypeClasses[toast.type],
          )}
        >
          <span className="text-sm">{toast.message}</span>
          <button
            onClick={() => hideToast(toast.id)}
            className="ml-2 text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

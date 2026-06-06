import { LoadingLines } from '../components/ui/LoadingLines';

export default function Loading() {
  return (
    <div className="min-h-[50vh] flex items-center justify-center bg-ivory">
      <LoadingLines />
    </div>
  );
}

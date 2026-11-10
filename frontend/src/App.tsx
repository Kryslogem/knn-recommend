import { useQuery } from '@tanstack/react-query'
import { Route, Routes } from 'react-router-dom'
import { api, type Health } from './api/client'

// Giai đoạn 0: trang trạng thái kết nối backend.
// Các route đầy đủ (PLAN.md mục 11) sẽ được thêm ở giai đoạn 6.
function StatusPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => api<Health>('/health'),
  })

  return (
    <main className="mx-auto max-w-xl p-8">
      <h1 className="text-2xl font-bold">KNN Movie Recommender</h1>
      <p className="mt-1 text-slate-500">Hệ thống đề xuất phim cá nhân hóa bằng KNNBaseline</p>

      <section className="mt-6 rounded-lg border border-slate-200 p-4">
        <h2 className="font-semibold">Trạng thái backend</h2>
        {isLoading && <p className="mt-2 text-slate-500">Đang kiểm tra…</p>}
        {error && (
          <p className="mt-2 text-red-600">
            Không kết nối được backend. Hãy chạy <code>uvicorn backend.app.main:app --port 8000</code>.
          </p>
        )}
        {data && (
          <ul className="mt-2 space-y-1 text-sm">
            <li>
              API: <span className="font-medium text-green-700">{data.status}</span> (v{data.version})
            </li>
            <li>
              Mô hình:{' '}
              {data.model_loaded ? (
                <span className="text-green-700">đã nạp</span>
              ) : (
                <span className="text-amber-600">chưa nạp (sẽ có ở giai đoạn 4–5)</span>
              )}
            </li>
          </ul>
        )}
      </section>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<StatusPage />} />
    </Routes>
  )
}

import React from 'react';

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-xl bg-slate-800 border border-slate-700 rounded-2xl p-8 shadow-2xl">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/10 text-blue-400 text-3xl mb-4">
          📦
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
          Hệ thống Quản lý Kho Thông minh AI
        </h1>
        <p className="text-slate-400 mb-6">
          Đề tài 07 — Tích hợp Google Gemini & Động cơ Dự phòng Heuristic
        </p>
        <div className="grid grid-cols-2 gap-4 text-left text-sm bg-slate-900/60 p-4 rounded-xl border border-slate-700/50 mb-6">
          <div>
            <span className="text-slate-500 block">Trạng thái Backend:</span>
            <span className="text-emerald-400 font-semibold">● Sẵn sàng (FastAPI)</span>
          </div>
          <div>
            <span className="text-slate-500 block">Cơ sở dữ liệu:</span>
            <span className="text-emerald-400 font-semibold">● 9 Bảng ACID (SQLite)</span>
          </div>
        </div>
        <p className="text-xs text-slate-500">
          Khung ứng dụng Giai đoạn 0 đã được thiết lập thành công.
        </p>
      </div>
    </div>
  );
}

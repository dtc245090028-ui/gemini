import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Package,
  Calendar,
  Zap,
  ShieldAlert,
  ArrowRight,
  Info,
  CheckCircle2,
  Clock,
  Flame,
  Archive,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { apiClient } from '../api/client';
import Badge from '../components/Badge';

export const AIAssistant = ({ onNavigateToImport }) => {
  const [activeSubTab, setActiveSubTab] = useState('monthly'); // 'monthly' | 'restock' | 'anomalies'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 1. Data Báo cáo tháng
  const [monthlyData, setMonthlyData] = useState(null);
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());

  // 2. Data Gợi ý nhập hàng
  const [restockData, setRestockData] = useState(null);

  // 3. Data Biến động bất thường
  const [anomalyData, setAnomalyData] = useState(null);

  // Fetch Báo cáo tháng
  const handleFetchMonthlyReport = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.ai.getMonthlyReport(month, year, forceRefresh);
      setMonthlyData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể sinh báo cáo AI');
    } finally {
      setLoading(false);
    }
  };

  // Fetch Gợi ý nhập hàng
  const handleFetchRestock = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.ai.getRestockSuggestions(30, forceRefresh);
      setRestockData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể lấy gợi ý nhập hàng');
    } finally {
      setLoading(false);
    }
  };

  // Fetch Bất thường
  const handleFetchAnomalies = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.ai.getAnomalies(30, forceRefresh);
      setAnomalyData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể quét bất thường');
    } finally {
      setLoading(false);
    }
  };

  // Tự động tải dữ liệu ban đầu cho tab đang chọn (dùng cache nếu có)
  useEffect(() => {
    if (activeSubTab === 'monthly' && !monthlyData) handleFetchMonthlyReport(false);
    if (activeSubTab === 'restock' && !restockData) handleFetchRestock(false);
    if (activeSubTab === 'anomalies' && !anomalyData) handleFetchAnomalies(false);
  }, [activeSubTab]);

  return (
    <div className="space-y-6">
      {/* Top Banner AI */}
      <div className="bg-gradient-to-r from-wood-950 via-wood-900 to-wood-800 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden border border-wood-700/50">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-wood-500/20 text-wood-200 text-xs font-semibold border border-wood-500/30 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>Google Gemini & Heuristic Fallback Engine</span>
            </div>
            <h2 className="text-2xl font-bold font-serif tracking-tight text-white">Trung Tâm Trợ Lý Kho Thông Minh</h2>
            <p className="text-wood-200/90 text-xs mt-1 leading-relaxed font-sans">
              Giải quyết 3 bài toán lớn của Đề tài 07: Tự động tổng hợp báo cáo tháng, gợi ý bổ sung hàng theo tốc độ tiêu thụ thực tế và nhận diện các rủi ro kho bãi bất thường.
            </p>
          </div>

          {/* Sub Navigation Buttons */}
          <div className="flex flex-wrap md:flex-nowrap gap-2 bg-wood-950/40 p-1.5 rounded-btn border border-white/10 backdrop-blur-md">
            <button
              onClick={() => setActiveSubTab('monthly')}
              className={`px-3 py-2 rounded-btn text-xs font-semibold transition-all cursor-pointer ${
                activeSubTab === 'monthly'
                  ? 'bg-wood-600 text-white shadow-sm'
                  : 'text-wood-200 hover:text-white hover:bg-white/5'
              }`}
            >
              1. Báo cáo tháng
            </button>
            <button
              onClick={() => setActiveSubTab('restock')}
              className={`px-3 py-2 rounded-btn text-xs font-semibold transition-all cursor-pointer ${
                activeSubTab === 'restock'
                  ? 'bg-wood-600 text-white shadow-sm'
                  : 'text-wood-200 hover:text-white hover:bg-white/5'
              }`}
            >
              2. Gợi ý nhập hàng
            </button>
            <button
              onClick={() => setActiveSubTab('anomalies')}
              className={`px-3 py-2 rounded-btn text-xs font-semibold transition-all cursor-pointer ${
                activeSubTab === 'anomalies'
                  ? 'bg-wood-600 text-white shadow-sm'
                  : 'text-wood-200 hover:text-white hover:bg-white/5'
              }`}
            >
              3. Biến động bất thường
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rust-50 border border-rust-200 rounded-btn flex items-center gap-2.5 text-xs text-rust-800">
          <AlertTriangle className="w-4 h-4 text-rust-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ==================================================================== */}
      {/* PHÂN HỆ 1: BÁO CÁO THÁNG */}
      {/* ==================================================================== */}
      {activeSubTab === 'monthly' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="card-warm p-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Calendar className="w-4 h-4 text-wood-500" />
              <span className="text-xs font-semibold text-charcoal">Chọn kỳ báo cáo:</span>
              <select
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
                className="py-1.5 px-3 bg-white border border-wood-200 rounded-btn text-xs font-medium text-charcoal focus:outline-none focus:ring-2 focus:ring-wood-500/20"
              >
                {[...Array(12)].map((_, i) => (
                  <option key={i + 1} value={i + 1}>
                    Tháng {i + 1}
                  </option>
                ))}
              </select>
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="py-1.5 px-3 bg-white border border-wood-200 rounded-btn text-xs font-medium text-charcoal focus:outline-none focus:ring-2 focus:ring-wood-500/20"
              >
                {[2024, 2025, 2026, 2027].map((y) => (
                  <option key={y} value={y}>
                    Năm {y}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => handleFetchMonthlyReport(true)}
              disabled={loading}
              className="btn-primary text-xs flex items-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <Sparkles className="w-4 h-4 text-amber-300" />
              )}
              <span>Yêu cầu AI phân tích kỳ này</span>
            </button>
          </div>

          {loading && !monthlyData && (
            <div className="card-warm p-12 flex flex-col items-center justify-center text-center">
              <Loader2 className="w-8 h-8 text-amber-600 animate-spin mb-3" />
              <p className="text-sm font-semibold text-wood-950 font-serif">AI đang phân tích và tổng hợp số liệu báo cáo...</p>
              <p className="text-xs text-charcoal/60 mt-1 font-sans">Đang xử lý dữ liệu nhập - xuất - tồn kỳ này.</p>
            </div>
          )}

          {monthlyData && (
            <div className="space-y-6">
              {/* Provider Info Banner */}
              <div className="p-3.5 bg-wood-100 rounded-btn border border-wood-200 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-charcoal">Động cơ tính toán:</span>
                  <Badge variant={monthlyData.is_fallback ? 'amber' : 'forest'}>
                    {monthlyData.is_fallback
                      ? '⚡ Heuristic Fallback Engine (Offline Safe < 50ms)'
                      : '🤖 Google Gemini 3.5 Flash-Lite (Online LLM)'}
                  </Badge>
                  {monthlyData.is_cached && (
                    <Badge variant="blue">
                      📦 Đã lưu đệm trong ngày (0 Quota)
                    </Badge>
                  )}
                </div>
                <span className="text-charcoal/60">Kỳ: {monthlyData.period}</span>
              </div>

              {/* Metrics Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="card-warm p-4">
                  <p className="text-xs text-charcoal/70">Mặt hàng quản lý</p>
                  <p className="text-xl font-bold font-serif text-wood-950 mt-1">
                    {monthlyData.metrics.total_products} <span className="text-xs font-normal text-charcoal/60 font-sans">({monthlyData.metrics.active_products} hoạt động)</span>
                  </p>
                </div>
                <div className="card-warm p-4">
                  <p className="text-xs text-charcoal/70">Tổng lượng nhập kho</p>
                  <p className="text-xl font-bold font-serif text-forest-700 mt-1">
                    +{monthlyData.metrics.total_imports_qty} <span className="text-xs font-normal text-charcoal/60 font-sans">sp</span>
                  </p>
                </div>
                <div className="card-warm p-4">
                  <p className="text-xs text-charcoal/70">Tổng lượng xuất kho</p>
                  <p className="text-xl font-bold font-serif text-wood-700 mt-1">
                    -{monthlyData.metrics.total_exports_qty} <span className="text-xs font-normal text-charcoal/60 font-sans">sp</span>
                  </p>
                </div>
                <div className="card-warm p-4">
                  <p className="text-xs text-charcoal/70">Dưới mức tối thiểu</p>
                  <p className="text-xl font-bold font-serif text-rust-700 mt-1">
                    {monthlyData.metrics.low_stock_count} <span className="text-xs font-normal text-charcoal/60 font-sans">sp</span>
                  </p>
                </div>
              </div>

              {/* Executive Summary AI Box */}
              <div className="card-warm bg-gradient-to-br from-wood-50/70 via-white to-amber-50/40 p-6 border-wood-200 space-y-4">
                <div className="flex items-center gap-2 text-wood-950 font-bold font-serif text-base">
                  <Sparkles className="w-5 h-5 text-wood-700" />
                  <span>Nhận Xét Điều Hành Kho Vận (Executive Summary)</span>
                </div>
                <p className="text-charcoal text-xs sm:text-sm leading-relaxed font-sans whitespace-pre-line bg-white/80 p-4 rounded-btn border border-wood-200 shadow-xs">
                  {monthlyData.executive_summary}
                </p>

                {/* Recommendations */}
                {monthlyData.recommendations?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold font-serif text-wood-950 uppercase tracking-wider mb-2">Khuyến nghị điều hành từ AI:</h4>
                    <div className="space-y-2">
                      {monthlyData.recommendations.map((rec, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-charcoal bg-white p-3 rounded-btn border border-wood-200">
                          <CheckCircle2 className="w-4 h-4 text-forest-600 shrink-0 mt-0.5" />
                          <span>{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* PHÂN HỆ 2: GỢI Ý NHẬP HÀNG TỐI ƯU */}
      {/* ==================================================================== */}
      {activeSubTab === 'restock' && (
        <div className="space-y-6">
          <div className="card-warm p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-wood-700" />
              <span className="text-xs font-semibold text-charcoal">
                Thuật toán phân tích dựa trên: Tồn kho hiện có, Tồn an toàn và Vận tốc xuất 30 ngày qua
              </span>
            </div>
            <button
              onClick={() => handleFetchRestock(true)}
              disabled={loading}
              className="btn-secondary text-xs flex items-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              <span>Tính toán lại</span>
            </button>
          </div>

          {loading && !restockData && (
            <div className="card-warm p-12 flex flex-col items-center justify-center text-center">
              <Loader2 className="w-8 h-8 text-amber-600 animate-spin mb-3" />
              <p className="text-sm font-semibold text-wood-950 font-serif">Đang phân tích tồn kho và tính toán gợi ý nhập hàng...</p>
              <p className="text-xs text-charcoal/60 mt-1 font-sans">Đang đánh giá tốc độ xuất và dự báo ngày hết hàng.</p>
            </div>
          )}

          {restockData && (
            <div className="space-y-6">
              {/* Provider Info Banner */}
              <div className="p-3.5 bg-wood-100 rounded-btn border border-wood-200 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-charcoal">Động cơ tính toán:</span>
                  <Badge variant={restockData.is_fallback ? 'amber' : 'forest'}>
                    {restockData.is_fallback
                      ? '⚡ Heuristic Fallback Engine (Offline Safe < 50ms)'
                      : '🤖 Google Gemini 3.5 Flash-Lite (Online LLM)'}
                  </Badge>
                  {restockData.is_cached && (
                    <Badge variant="blue">
                      📦 Đã lưu đệm trong ngày (0 Quota)
                    </Badge>
                  )}
                </div>
                <span className="text-charcoal/60">Phạm vi: {restockData.lookback_days || 30} ngày qua</span>
              </div>

              {/* Executive Summary */}
              <div className="card-warm bg-amber-50/60 p-4 border border-amber-200 text-xs text-wood-950 leading-relaxed font-medium flex items-center gap-3">
                <Info className="w-5 h-5 text-amber-700 shrink-0" />
                <span>{restockData.executive_summary}</span>
              </div>

              {/* Suggestions Table */}
              <div className="card-warm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-wood-100 text-wood-800 font-semibold border-b border-wood-200">
                      <tr>
                        <th className="py-3 px-4">Mã SKU</th>
                        <th className="py-3 px-4">Tên hàng hóa</th>
                        <th className="py-3 px-4 text-center">Tồn hiện tại</th>
                        <th className="py-3 px-4 text-center">Tồn an toàn</th>
                        <th className="py-3 px-4 text-center">Vận tốc bán (sp/ngày)</th>
                        <th className="py-3 px-4 text-center font-bold text-wood-950">Đề xuất nhập</th>
                        <th className="py-3 px-4 text-center">Mức ưu tiên</th>
                        <th className="py-3 px-4">Lý do gợi ý từ AI</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-wood-100">
                      {restockData.items.length === 0 ? (
                        <tr>
                          <td colSpan="8" className="text-center py-10 text-charcoal/50">
                            Kho hàng đang ở trạng thái an toàn tuyệt đối. Chưa cần bổ sung mặt hàng nào!
                          </td>
                        </tr>
                      ) : (
                        restockData.items.map((it) => (
                          <tr key={it.product_id} className="hover:bg-wood-50/70 transition-colors">
                            <td className="py-3.5 px-4 font-mono font-semibold text-wood-700">{it.product_code}</td>
                            <td className="py-3.5 px-4 font-medium text-wood-950">{it.product_name}</td>
                            <td className="py-3.5 px-4 text-center font-bold text-rust-700">{it.current_stock}</td>
                            <td className="py-3.5 px-4 text-center text-charcoal/70">{it.min_stock}</td>
                            <td className="py-3.5 px-4 text-center font-mono text-charcoal/80">{it.daily_velocity}</td>
                            <td className="py-3.5 px-4 text-center">
                              <span className="font-bold text-amber-800 bg-amber-50 px-2.5 py-1 rounded-btn border border-amber-200">
                                +{it.suggested_quantity}
                              </span>
                            </td>
                            <td className="py-3.5 px-4 text-center">
                              <Badge
                                variant={
                                  it.priority === 'HIGH'
                                    ? 'red'
                                    : it.priority === 'MEDIUM'
                                    ? 'amber'
                                    : 'wood'
                                }
                              >
                                {it.priority === 'HIGH' ? 'Khẩn cấp (HIGH)' : it.priority === 'MEDIUM' ? 'Cần nhập (MED)' : 'Thấp (LOW)'}
                              </Badge>
                            </td>
                            <td className="py-3.5 px-4 text-charcoal/80 max-w-sm leading-relaxed">{it.reason}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================================================================== */}
      {/* PHÂN HỆ 3: TÓM TẮT BIẾN ĐỘNG BẤT THƯỜNG */}
      {/* ==================================================================== */}
      {activeSubTab === 'anomalies' && (
        <div className="space-y-6">
          <div className="card-warm p-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rust-600" />
              <span className="text-xs font-semibold text-charcoal">
                Thuật toán quét 2 biến động rủi ro chính: Xuất tăng vọt (&gt;200%) và Hàng tồn kho chết (&gt;30 ngày)
              </span>
            </div>
            <button
              onClick={() => handleFetchAnomalies(true)}
              disabled={loading}
              className="btn-danger text-xs flex items-center gap-2 disabled:opacity-60 cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <Zap className="w-4 h-4 text-amber-300" />
              )}
              <span>Quét lại rủi ro</span>
            </button>
          </div>

          {loading && !anomalyData && (
            <div className="card-warm p-12 flex flex-col items-center justify-center text-center">
              <Loader2 className="w-8 h-8 text-rust-600 animate-spin mb-3" />
              <p className="text-sm font-semibold text-wood-950 font-serif">Đang quét phát hiện biến động bất thường và tồn đọng...</p>
              <p className="text-xs text-charcoal/60 mt-1 font-sans">Đang phân tích rủi ro xuất tăng đột biến &gt;200% và hàng tồn &gt;30 ngày.</p>
            </div>
          )}

          {anomalyData && (
            <div className="space-y-6">
              {/* Provider Info Banner */}
              <div className="p-3.5 bg-wood-100 rounded-btn border border-wood-200 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-charcoal">Động cơ tính toán:</span>
                  <Badge variant={anomalyData.is_fallback ? 'amber' : 'forest'}>
                    {anomalyData.is_fallback
                      ? '⚡ Heuristic Fallback Engine (Offline Safe < 50ms)'
                      : '🤖 Google Gemini 3.5 Flash-Lite (Online LLM)'}
                  </Badge>
                  {anomalyData.is_cached && (
                    <Badge variant="blue">
                      📦 Đã lưu đệm trong ngày (0 Quota)
                    </Badge>
                  )}
                </div>
                <span className="text-charcoal/60">Phạm vi: {anomalyData.lookback_days || 30} ngày qua</span>
              </div>

              <div className="card-warm bg-rust-50/50 p-4 border border-rust-200 text-xs text-rust-950 leading-relaxed font-medium flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-rust-600 shrink-0" />
                <span>{anomalyData.executive_summary}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {anomalyData.anomalies.length === 0 ? (
                  <div className="col-span-2 card-warm p-12 text-center text-charcoal/50 text-xs">
                    Kho vận đang vận hành ổn định! Không ghi nhận đột biến hay hàng ứ đọng bất thường.
                  </div>
                ) : (
                  anomalyData.anomalies.map((ano, idx) => {
                    const isSurge = ano.anomaly_type === 'SURGE_EXPORT';
                    return (
                      <div
                        key={idx}
                        className={`p-5 rounded-btn border shadow-xs space-y-3 transition-all ${
                          isSurge
                            ? 'bg-gradient-to-br from-rust-50/60 to-white border-rust-200'
                            : 'card-warm border-wood-200'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {isSurge ? (
                              <Flame className="w-5 h-5 text-rust-600" />
                            ) : (
                              <Archive className="w-5 h-5 text-wood-600" />
                            )}
                            <h4 className="font-bold font-serif text-wood-950 text-sm">{ano.product_name}</h4>
                          </div>
                          <Badge variant={isSurge ? 'red' : 'gray'}>
                            {isSurge ? 'Xuất tăng đột biến' : 'Hàng tồn lâu (>30 ngày)'}
                          </Badge>
                        </div>

                        <p className="text-xs text-charcoal/80 leading-relaxed font-sans">{ano.description}</p>

                        <div className="p-3 bg-white/80 rounded-btn border border-wood-200/80 text-xs">
                          <span className="font-semibold text-charcoal block mb-1">💡 Đề xuất hành động từ AI:</span>
                          <span className="text-charcoal/80">{ano.suggested_action}</span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AIAssistant;

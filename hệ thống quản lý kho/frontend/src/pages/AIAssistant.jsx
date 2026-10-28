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
  MessageSquare,
  Send,
  Copy,
  Check,
  Download,
  Search,
} from 'lucide-react';
import { apiClient } from '../api/client';
import Badge from '../components/Badge';
import { Loader } from '../components/Loader';

const renderFormattedAnswer = (text) => {
  if (!text) return null;
  return text.split('\n').map((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={idx} className="h-2" />;

    if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
      return (
        <p key={idx} className="font-bold text-[var(--text-primary)] text-xs mt-2 mb-1">
          {trimmed.slice(2, -2)}
        </p>
      );
    }

    if (trimmed.startsWith('•') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.replace(/^[•\-\*]\s*/, '');
      const parts = content.split(/(\*\*.*?\*\*)/g);
      return (
        <div key={idx} className="flex items-start gap-2 text-xs text-[var(--text-secondary)] pl-2 py-0.5">
          <span className="text-[var(--semantic-ai)] font-bold shrink-0">•</span>
          <span>
            {parts.map((p, pIdx) => {
              if (p.startsWith('**') && p.endsWith('**')) {
                return <strong key={pIdx} className="font-bold text-[var(--text-primary)]">{p.slice(2, -2)}</strong>;
              }
              return p;
            })}
          </span>
        </div>
      );
    }

    const parts = trimmed.split(/(\*\*.*?\*\*)/g);
    return (
      <p key={idx} className="text-xs text-[var(--text-secondary)] leading-relaxed">
        {parts.map((p, pIdx) => {
          if (p.startsWith('**') && p.endsWith('**')) {
            return <strong key={pIdx} className="font-bold text-[var(--text-primary)]">{p.slice(2, -2)}</strong>;
          }
          return p;
        })}
      </p>
    );
  });
};

const getTodayStr = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

export const AIAssistant = ({ onNavigateToImport }) => {
  const [activeSubTab, setActiveSubTab] = useState('monthly'); // 'monthly' | 'restock' | 'anomalies'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 1. Data Báo cáo Nhập - Xuất - Tồn theo kỳ / khoảng ngày
  const [monthlyData, setMonthlyData] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [isExportingSummary, setIsExportingSummary] = useState(false);
  const now = new Date();
  const [periodType, setPeriodType] = useState('month'); // 'month' | 'week' | 'day' | 'custom'
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [targetDate, setTargetDate] = useState(getTodayStr);
  const [customStartDate, setCustomStartDate] = useState(() => {
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    return `${first.getFullYear()}-${String(first.getMonth() + 1).padStart(2, '0')}-01`;
  });
  const [customEndDate, setCustomEndDate] = useState(getTodayStr);

  // 2. Data Gợi ý nhập hàng
  const [restockData, setRestockData] = useState(null);
  const [restockDays, setRestockDays] = useState(30);

  // 3. Data Biến động bất thường
  const [anomalyData, setAnomalyData] = useState(null);
  const [anomalyDays, setAnomalyDays] = useState(30);

  // 4. Interactive Q&A State
  const [questionInput, setQuestionInput] = useState('');
  const [isSmartKhoRequired, setIsSmartKhoRequired] = useState(false);
  const [askingAi, setAskingAi] = useState(false);
  const [qaResponse, setQaResponse] = useState(null);
  const [qaError, setQaError] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleAskAI = async (customQ = null) => {
    const q = (customQ || questionInput).trim();
    if (!q) return;
    if (customQ) setQuestionInput(customQ);

    setAskingAi(true);
    setQaError(null);
    try {
      const res = await apiClient.ai.ask(q, month, year, isSmartKhoRequired);
      setQaResponse(res.data);
    } catch (err) {
      console.error('Lỗi khi gửi câu hỏi đến AI:', err);
      setQaError(err.response?.data?.detail || 'Không thể kết nối đến Trợ lý AI vào lúc này.');
    } finally {
      setAskingAi(false);
    }
  };

  const handleCopyAnswer = () => {
    if (!qaResponse?.answer) return;
    navigator.clipboard.writeText(qaResponse.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getPeriodDateRange = () => {
    if (periodType === 'month') {
      const lastDay = new Date(year, month, 0).getDate();
      return {
        fromDate: `${year}-${String(month).padStart(2, '0')}-01T00:00:00`,
        toDate: `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}T23:59:59`,
      };
    } else if (periodType === 'day') {
      return {
        fromDate: `${targetDate}T00:00:00`,
        toDate: `${targetDate}T23:59:59`,
      };
    } else if (periodType === 'week') {
      const d = new Date(targetDate);
      const day = d.getDay();
      const diff = d.getDate() - day + (day === 0 ? -6 : 1);
      const startOfWeek = new Date(d.setDate(diff));
      const endOfWeek = new Date(startOfWeek);
      endOfWeek.setDate(startOfWeek.getDate() + 6);
      return {
        fromDate: `${startOfWeek.toISOString().slice(0, 10)}T00:00:00`,
        toDate: `${endOfWeek.toISOString().slice(0, 10)}T23:59:59`,
      };
    } else {
      return {
        fromDate: `${customStartDate}T00:00:00`,
        toDate: `${customEndDate}T23:59:59`,
      };
    }
  };

  const handleExportSummaryExcel = async () => {
    setIsExportingSummary(true);
    setSummaryError(null);
    try {
      const { fromDate, toDate } = getPeriodDateRange();
      const res = await apiClient.reports.exportExcel(fromDate, toDate);
      const blob = new Blob([res.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      let filename = `bao_cao_nhap_xuat_ton_${fromDate.slice(0, 10)}_${toDate.slice(0, 10)}.xlsx`;
      const disposition = res.headers?.['content-disposition'];
      if (disposition) {
        const match = disposition.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Lỗi khi xuất file Excel:', err);
      setSummaryError('Không thể xuất file Excel Báo cáo Nhập Xuất Tồn. Vui lòng thử lại.');
    } finally {
      setIsExportingSummary(false);
    }
  };

  // Fetch Báo cáo kỳ / khoảng ngày (Đồng thời cả Trợ lý AI và Bảng Nhập Xuất Tồn 76 SP)
  const handleFetchMonthlyReport = async (forceRefresh = false) => {
    setLoading(true);
    setSummaryLoading(true);
    setError(null);
    setSummaryError(null);
    const { fromDate, toDate } = getPeriodDateRange();

    try {
      const extra = { period_type: periodType };
      if (periodType === 'day' || periodType === 'week') {
        extra.target_date = targetDate;
      } else if (periodType === 'custom') {
        extra.start_date = customStartDate;
        extra.end_date = customEndDate;
      }

      const [aiRes, sumRes] = await Promise.allSettled([
        apiClient.ai.getMonthlyReport(month, year, forceRefresh, extra),
        apiClient.reports.getSummary(fromDate, toDate),
      ]);

      if (aiRes.status === 'fulfilled') {
        setMonthlyData(aiRes.value.data);
      } else {
        setError(aiRes.reason?.response?.data?.detail || 'Không thể sinh báo cáo AI');
      }

      if (sumRes.status === 'fulfilled') {
        setSummaryData(sumRes.value.data);
      } else {
        setSummaryError(sumRes.reason?.response?.data?.detail || 'Không thể tải bảng số liệu nhập xuất tồn.');
      }
    } finally {
      setLoading(false);
      setSummaryLoading(false);
    }
  };

  // Fetch Gợi ý nhập hàng
  const handleFetchRestock = async (forceRefresh = false, customLookback = restockDays) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.ai.getRestockSuggestions(customLookback, forceRefresh);
      setRestockData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể lấy gợi ý nhập hàng');
    } finally {
      setLoading(false);
    }
  };

  // Fetch Bất thường
  const handleFetchAnomalies = async (forceRefresh = false, customLookback = anomalyDays) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.ai.getAnomalies(customLookback, forceRefresh);
      setAnomalyData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể quét bất thường');
    } finally {
      setLoading(false);
    }
  };

  // Tự động tải dữ liệu ban đầu cho tab đang chọn (dùng bản lưu nếu có)
  useEffect(() => {
    if (activeSubTab === 'monthly' && !monthlyData) handleFetchMonthlyReport(false);
    if (activeSubTab === 'restock' && !restockData) handleFetchRestock(false);
    if (activeSubTab === 'anomalies' && !anomalyData) handleFetchAnomalies(false);
  }, [activeSubTab]);

  return (
    <div className="space-y-6">
      {/* Top Banner AI */}
      <div className="bg-[var(--wood-900)] rounded-card p-4 sm:p-6 text-[var(--wood-light)] shadow-md relative overflow-hidden border border-[var(--wood-700)]">
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="max-w-2xl min-w-0">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-pill bg-white/10 text-[var(--wood-muted)] text-xs font-medium border border-white/15 mb-2">
              <Sparkles className="w-3.5 h-3.5 text-[var(--wood-300)] shrink-0" />
              <span className="truncate">Google Gemini & Heuristic Fallback Engine</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold font-serif tracking-tight text-[var(--wood-light)]">Trung tâm trợ lý kho thông minh</h2>
            <p className="text-[var(--wood-muted)] text-xs mt-1 leading-relaxed font-sans">
              Giải quyết 3 bài toán lớn của Đề tài 07: Tự động tổng hợp báo cáo tháng, gợi ý bổ sung hàng theo tốc độ tiêu thụ thực tế và nhận diện các rủi ro kho bãi bất thường.
            </p>
          </div>

          {/* Sub Navigation Buttons */}
          <div className="flex flex-wrap gap-1.5 bg-black/25 p-1.5 rounded-btn border border-white/10 backdrop-blur-md self-start lg:self-auto shrink-0">
            <button
              onClick={() => setActiveSubTab('monthly')}
              className={`px-3 py-2 rounded-btn text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeSubTab === 'monthly'
                  ? 'bg-[var(--wood-accent)] text-white shadow-xs'
                  : 'text-[var(--wood-muted)] hover:text-white hover:bg-white/10'
              }`}
            >
              1. Báo cáo tháng
            </button>
            <button
              onClick={() => setActiveSubTab('restock')}
              className={`px-3 py-2 rounded-btn text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeSubTab === 'restock'
                  ? 'bg-[var(--wood-accent)] text-white shadow-xs'
                  : 'text-[var(--wood-muted)] hover:text-white hover:bg-white/10'
              }`}
            >
              2. Gợi ý nhập hàng
            </button>
            <button
              onClick={() => setActiveSubTab('anomalies')}
              className={`px-3 py-2 rounded-btn text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                activeSubTab === 'anomalies'
                  ? 'bg-[var(--wood-accent)] text-white shadow-xs'
                  : 'text-[var(--wood-muted)] hover:text-white hover:bg-white/10'
              }`}
            >
              3. Biến động bất thường
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] rounded-card flex items-center gap-2.5 text-xs text-[var(--semantic-alert)] font-medium">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ==================================================================== */}
      {/* PHÂN HỆ 1: BÁO CÁO THÁNG / KHOẢNG THỜI GIAN */}
      {/* ==================================================================== */}
      {activeSubTab === 'monthly' && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="card-warm p-3.5 sm:p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Calendar className="w-4 h-4 text-[var(--wood-accent)] shrink-0" />
              <span className="text-xs font-semibold text-[var(--text-secondary)]">Mốc phân tích:</span>
              <select
                value={periodType}
                onChange={(e) => setPeriodType(e.target.value)}
                className="input-wood text-xs w-auto"
              >
                <option value="month">Theo tháng</option>
                <option value="week">Theo tuần</option>
                <option value="day">Theo ngày</option>
                <option value="custom">Khoảng ngày</option>
              </select>

              {periodType === 'month' && (
                <>
                  <select
                    value={month}
                    onChange={(e) => setMonth(Number(e.target.value))}
                    className="input-wood text-xs w-auto"
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
                    className="input-wood text-xs w-auto"
                  >
                    {[2024, 2025, 2026, 2027].map((y) => (
                      <option key={y} value={y}>
                        Năm {y}
                      </option>
                    ))}
                  </select>
                </>
              )}

              {(periodType === 'day' || periodType === 'week') && (
                <input
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="input-wood text-xs font-mono w-auto"
                />
              )}

              {periodType === 'custom' && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="input-wood text-xs font-mono w-auto"
                  />
                  <span className="text-xs text-[var(--text-muted)]">→</span>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="input-wood text-xs font-mono w-auto"
                  />
                </div>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleFetchMonthlyReport(false)}
                disabled={loading}
                className="btn-ai text-xs flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer flex-1 sm:flex-initial"
              >
                {loading ? <Loader variant="inline" /> : <Sparkles className="w-4 h-4" />}
                <span>{loading ? 'Đang tải...' : 'Xem / Phân tích kỳ này'}</span>
              </button>

              <button
                onClick={() => handleFetchMonthlyReport(true)}
                disabled={loading}
                className="btn-outline text-xs flex items-center justify-center gap-1.5 disabled:opacity-60 cursor-pointer shrink-0"
                title="Bỏ qua bản lưu và yêu cầu AI phân tích lại từ đầu"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Tạo lại</span>
              </button>

              <button
                onClick={handleExportSummaryExcel}
                disabled={isExportingSummary || summaryLoading}
                className="btn-primary text-xs flex items-center justify-center gap-1.5 disabled:opacity-60 cursor-pointer shrink-0"
                title="Xuất Báo cáo Nhập Xuất Tồn ra file Excel (.xlsx)"
              >
                {isExportingSummary ? <Loader variant="inline" /> : <Download className="w-3.5 h-3.5" />}
                <span>{isExportingSummary ? 'Đang xuất...' : 'Xuất Excel Báo Cáo'}</span>
              </button>
            </div>
          </div>

          {loading && !monthlyData && (
            <div className="card-warm p-8">
              <Loader
                variant="page"
                message="Trợ lý AI đang phân tích dữ liệu nhập - xuất - tồn và lập báo cáo..."
                isAi={true}
              />
            </div>
          )}

          {monthlyData && (
            <div className="space-y-6">
              {/* Provider Info Banner */}
              <div className="p-3.5 bg-[var(--bg-linen)] rounded-card border border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-[var(--text-secondary)]">Động cơ tính toán:</span>
                  <Badge variant={monthlyData.is_fallback ? 'amber' : 'forest'}>
                    {monthlyData.is_fallback
                      ? 'Heuristic Fallback Engine (Dự phòng / Không biến động)'
                      : 'Google Gemini 3.5 Flash-Lite (Online LLM)'}
                  </Badge>
                  {monthlyData.is_cached && (
                    <Badge variant="wood">
                      <Clock className="w-3 h-3 mr-1 inline-block" />
                      Đã lưu lúc {monthlyData.cached_at || 'hôm nay'}
                    </Badge>
                  )}
                </div>
                <span className="text-[var(--text-muted)] font-mono">
                  Kỳ: {monthlyData.period}
                  {monthlyData.start_date && monthlyData.end_date ? ` (${monthlyData.start_date} → ${monthlyData.end_date})` : ''}
                </span>
              </div>

              {/* Metrics Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="card-warm p-4">
                  <p className="text-xs text-[var(--text-secondary)]">Mặt hàng quản lý</p>
                  <p className="text-xl font-bold font-serif text-[var(--text-primary)] mt-1">
                    {monthlyData.metrics.total_products} <span className="text-xs font-normal text-[var(--text-muted)] font-sans">({monthlyData.metrics.active_products} hoạt động)</span>
                  </p>
                </div>
                <div className="card-warm p-4">
                  <p className="text-xs text-[var(--text-secondary)]">Tổng lượng nhập kho</p>
                  <p className="text-xl font-bold font-serif text-[var(--semantic-success)] mt-1 font-mono">
                    +{monthlyData.metrics.total_imports_qty} <span className="text-xs font-normal text-[var(--text-muted)] font-sans">sp</span>
                  </p>
                </div>
                <div className="card-warm p-4">
                  <p className="text-xs text-[var(--text-secondary)]">Tổng lượng xuất kho</p>
                  <p className="text-xl font-bold font-serif text-[var(--text-primary)] mt-1 font-mono">
                    -{monthlyData.metrics.total_exports_qty} <span className="text-xs font-normal text-[var(--text-muted)] font-sans">sp</span>
                  </p>
                </div>
                <div className="card-warm p-4">
                  <p className="text-xs text-[var(--text-secondary)]">Dưới mức tối thiểu</p>
                  <p className="text-xl font-bold font-serif text-[var(--semantic-alert)] mt-1 font-mono">
                    {monthlyData.metrics.low_stock_count} <span className="text-xs font-normal text-[var(--text-muted)] font-sans">sp</span>
                  </p>
                </div>
              </div>

              {/* BẢNG BÁO CÁO NHẬP - XUẤT - TỒN KHO CHI TIẾT (76 MẶT HÀNG) */}
              <div className="card-warm p-4 sm:p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
                  <div>
                    <div className="flex items-center gap-2 text-[var(--text-primary)] font-bold font-serif text-base">
                      <Package className="w-5 h-5 text-[var(--wood-accent)]" />
                      <span>Báo Cáo Nhập - Xuất - Tồn Kho Hàng Hóa</span>
                      {summaryData && (
                        <span className="text-xs font-sans font-normal text-[var(--text-muted)]">
                          ({summaryData.items.length} mặt hàng)
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                      Công thức kế toán chuẩn: Tồn đầu + Nhập - Xuất + Điều chỉnh = Tồn cuối
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <div className="relative">
                      <input
                        type="text"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        placeholder="Tìm SKU, tên hàng..."
                        className="input-wood text-xs pl-8 pr-3 py-1.5 w-44 sm:w-56"
                      />
                      <Search className="w-3.5 h-3.5 text-[var(--text-muted)] absolute left-2.5 top-1/2 -translate-y-1/2" />
                    </div>

                    <button
                      onClick={handleExportSummaryExcel}
                      disabled={isExportingSummary || summaryLoading}
                      className="btn-primary text-xs flex items-center gap-1.5 px-3 py-1.5 cursor-pointer disabled:opacity-50"
                      title="Xuất bảng số liệu ra file Excel (.xlsx)"
                    >
                      {isExportingSummary ? <Loader variant="inline" /> : <Download className="w-3.5 h-3.5" />}
                      <span>{isExportingSummary ? 'Đang xuất...' : 'Xuất Excel'}</span>
                    </button>
                  </div>
                </div>

                {summaryLoading && !summaryData && (
                  <div className="py-8">
                    <Loader variant="page" message="Đang tải bảng số liệu nhập - xuất - tồn..." />
                  </div>
                )}

                {summaryError && (
                  <div className="p-3 bg-[var(--semantic-alert-bg)] border border-[var(--semantic-alert-border)] rounded-btn text-xs text-[var(--semantic-alert)] font-medium">
                    {summaryError}
                  </div>
                )}

                {summaryData && (
                  <div className="overflow-x-auto rounded-card border border-[var(--border-subtle)] max-h-[520px] overflow-y-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-[var(--bg-linen)] text-[var(--text-secondary)] font-semibold border-b border-[var(--border-subtle)] sticky top-0 z-10 shadow-xs">
                        <tr>
                          <th className="p-2.5 text-center w-10">STT</th>
                          <th className="p-2.5">Mã SKU</th>
                          <th className="p-2.5 min-w-[200px]">Tên hàng hóa</th>
                          <th className="p-2.5 text-center">ĐVT</th>
                          <th className="p-2.5 text-right">Tồn đầu</th>
                          <th className="p-2.5 text-right text-[var(--semantic-success)]">Nhập</th>
                          <th className="p-2.5 text-right text-[var(--semantic-alert)]">Xuất</th>
                          <th className="p-2.5 text-right text-amber-600">Đ.Chỉnh</th>
                          <th className="p-2.5 text-right font-bold text-[var(--text-primary)]">Tồn cuối</th>
                          <th className="p-2.5 text-right">Đơn giá</th>
                          <th className="p-2.5 text-right">Thành tiền</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-subtle)]">
                        {summaryData.items
                          .filter((it) => {
                            if (!searchTerm.trim()) return true;
                            const term = searchTerm.toLowerCase();
                            return (
                              it.product_code.toLowerCase().includes(term) ||
                              it.product_name.toLowerCase().includes(term) ||
                              (it.category_name && it.category_name.toLowerCase().includes(term))
                            );
                          })
                          .map((item, idx) => (
                            <tr key={item.product_id} className="hover:bg-[var(--bg-linen)]/60 transition-colors">
                              <td className="p-2 text-center text-[var(--text-muted)]">{idx + 1}</td>
                              <td className="p-2 font-mono font-semibold text-[var(--wood-accent)]">{item.product_code}</td>
                              <td className="p-2">
                                <div className="font-medium text-[var(--text-primary)]">{item.product_name}</div>
                                {item.category_name && (
                                  <div className="text-[10px] text-[var(--text-muted)]">{item.category_name}</div>
                                )}
                              </td>
                              <td className="p-2 text-center text-[var(--text-secondary)]">{item.unit}</td>
                              <td className="p-2 text-right font-mono">{item.opening_stock}</td>
                              <td className="p-2 text-right font-mono text-[var(--semantic-success)] font-medium">
                                {item.total_import > 0 ? `+${item.total_import}` : '0'}
                              </td>
                              <td className="p-2 text-right font-mono text-[var(--semantic-alert)] font-medium">
                                {item.total_export > 0 ? `-${item.total_export}` : '0'}
                              </td>
                              <td className="p-2 text-right font-mono text-amber-600">
                                {item.adjustment !== 0 ? (item.adjustment > 0 ? `+${item.adjustment}` : item.adjustment) : '0'}
                              </td>
                              <td className="p-2 text-right font-mono font-bold text-[var(--text-primary)]">
                                <span>{item.closing_stock}</span>
                                {item.is_low_stock && (
                                  <span className="ml-1.5 px-1.5 py-0.5 text-[9px] bg-[var(--semantic-alert-bg)] text-[var(--semantic-alert)] rounded font-semibold border border-[var(--semantic-alert-border)]">
                                    Dưới min
                                  </span>
                                )}
                              </td>
                              <td className="p-2 text-right font-mono text-[var(--text-muted)]">
                                {Math.round(item.standard_price).toLocaleString('vi-VN')} đ
                              </td>
                              <td className="p-2 text-right font-mono font-semibold text-[var(--text-primary)]">
                                {Math.round(item.total_value).toLocaleString('vi-VN')} đ
                              </td>
                            </tr>
                          ))}
                      </tbody>
                      <tfoot className="bg-[var(--bg-linen)] font-bold text-[var(--text-primary)] border-t-2 border-[var(--border-subtle)] sticky bottom-0 z-10 shadow-xs">
                        <tr>
                          <td colSpan={4} className="p-2.5 text-center uppercase tracking-wider text-xs">
                            Tổng cộng ({summaryData.total_products} SP)
                          </td>
                          <td className="p-2.5 text-right font-mono">{summaryData.total_opening}</td>
                          <td className="p-2.5 text-right font-mono text-[var(--semantic-success)]">+{summaryData.total_import}</td>
                          <td className="p-2.5 text-right font-mono text-[var(--semantic-alert)]">-{summaryData.total_export}</td>
                          <td className="p-2.5 text-right font-mono text-amber-600">{summaryData.total_adjustment || 0}</td>
                          <td className="p-2.5 text-right font-mono font-bold">{summaryData.total_closing}</td>
                          <td className="p-2.5 text-right">-</td>
                          <td className="p-2.5 text-right font-mono text-[var(--wood-accent)]">
                            {Math.round(summaryData.total_inventory_value).toLocaleString('vi-VN')} đ
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>

              {/* Executive Summary AI Box */}
              <div className="card-warm p-6 space-y-4">
                <div className="flex items-center gap-2 text-[var(--text-primary)] font-bold font-serif text-base">
                  <Sparkles className="w-5 h-5 text-[var(--semantic-ai)]" />
                  <span>Nhận xét điều hành kho vận (Executive Summary)</span>
                </div>
                <p className="text-[var(--text-primary)] text-xs leading-relaxed font-sans whitespace-pre-line bg-[var(--bg-card)] p-4 rounded-card border border-[var(--border-subtle)]">
                  {monthlyData.executive_summary}
                </p>

                {/* Recommendations */}
                {monthlyData.recommendations?.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold font-serif text-[var(--text-primary)] uppercase tracking-wider mb-2">Khuyến nghị điều hành từ AI:</h4>
                    <div className="space-y-2">
                      {monthlyData.recommendations.map((rec, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-primary)] bg-[var(--bg-card)] p-3 rounded-btn border border-[var(--border-subtle)]">
                          <CheckCircle2 className="w-4 h-4 text-[var(--semantic-success)] shrink-0 mt-0.5" />
                          <span>{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* ========================================================== */}
                {/* MỤC HỎI ĐÁP ĐIỀU HÀNH VỚI TRỢ LÝ AI (INTERACTIVE Q&A)     */}
                {/* ========================================================== */}
                <div className="pt-5 border-t border-[var(--border-subtle)] space-y-4">
                  <div>
                    <div className="flex items-center gap-2 text-xs font-bold font-serif text-[var(--text-primary)] uppercase tracking-wider mb-1">
                      <MessageSquare className="w-4 h-4 text-[var(--semantic-ai)]" />
                      <span>Hỏi đáp chuyên sâu cùng trợ lý AI:</span>
                    </div>
                    <p className="text-xs text-[var(--text-secondary)]">
                      Gửi câu hỏi hoặc tình huống cần tư vấn dựa trên số liệu thực tế của kỳ {month}/{year}.
                    </p>
                  </div>

                  {/* Suggestion Chips */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-xs text-[var(--text-secondary)] font-medium mr-1">Gợi ý câu hỏi:</span>
                    {[
                      'Cần ưu tiên xử lý các mặt hàng dưới mức tồn an toàn thế nào?',
                      'Đánh giá hiệu suất xuất kho kỳ này và đề xuất giải pháp?',
                      'Kế hoạch dự trữ và kiểm soát tồn kho cho tháng tới?',
                    ].map((sampleQ, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleAskAI(sampleQ)}
                        disabled={askingAi}
                        className="text-xs bg-[var(--bg-card)] hover:bg-[var(--bg-linen)] text-[var(--text-secondary)] px-2.5 py-1 rounded-pill border border-[var(--border-subtle)] transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {sampleQ}
                      </button>
                    ))}
                  </div>

                  {/* SmartKho Mode Toggle Checkbox */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1 pb-1">
                    <label className="inline-flex items-center gap-2 cursor-pointer select-none text-xs font-semibold text-[var(--text-primary)] bg-[var(--bg-card)] px-3 py-1.5 rounded-btn border border-[var(--border-subtle)] transition-all">
                      <input
                        type="checkbox"
                        checked={isSmartKhoRequired}
                        onChange={(e) => setIsSmartKhoRequired(e.target.checked)}
                        className="w-4 h-4 text-[var(--wood-accent)] rounded border-[var(--border-subtle)] cursor-pointer accent-[var(--wood-accent)]"
                      />
                      <span className="flex items-center gap-1">
                        <span>Yêu cầu về</span>
                        <span className="text-[var(--semantic-ai)] font-bold">#SmartKho</span>
                      </span>
                    </label>

                    <span className="text-xs text-[var(--text-secondary)]">
                      {isSmartKhoRequired ? (
                        <span className="text-[var(--semantic-ai)] font-medium">
                          Đã bật: AI sẽ kết hợp số liệu kho kỳ {month}/{year} và chèn các đề mục báo cáo.
                        </span>
                      ) : (
                        <span className="text-[var(--text-muted)]">
                          Đang tắt: Gửi thuần câu hỏi, để AI được tự do trả lời bất kỳ câu hỏi nào.
                        </span>
                      )}
                    </span>
                  </div>

                  {/* Input Form */}
                  <form onSubmit={(e) => { e.preventDefault(); handleAskAI(); }} className="space-y-2">
                    <div className="relative">
                      <textarea
                        value={questionInput}
                        onChange={(e) => setQuestionInput(e.target.value)}
                        placeholder={
                          isSmartKhoRequired
                            ? `Nhập câu hỏi/yêu cầu điều hành kho kỳ ${month}/${year} (AI sẽ chèn số liệu kho và cấu trúc đề mục báo cáo)...`
                            : "Nhập bất kỳ câu hỏi nào bạn muốn hỏi AI (AI tự do trả lời, không chèn báo cáo kho)..."
                        }
                        rows={2}
                        className="w-full text-xs p-3 input-wood resize-none pr-28"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleAskAI();
                          }
                        }}
                      />
                      <button
                        type="submit"
                        disabled={askingAi || !questionInput.trim()}
                        className="absolute right-2 bottom-2.5 btn-ai inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold disabled:opacity-50 transition-all cursor-pointer min-w-[95px] justify-center"
                      >
                        {askingAi ? (
                          <Loader variant="inline" />
                        ) : (
                          <Send className="w-3.5 h-3.5" />
                        )}
                        <span>{askingAi ? 'Đang hỏi...' : 'Gửi câu hỏi'}</span>
                      </button>
                    </div>
                  </form>

                  {qaError && (
                    <div className="p-3 bg-[var(--semantic-alert)]/10 border border-[var(--semantic-alert)]/30 rounded-card flex items-center gap-2 text-xs text-[var(--semantic-alert)] font-medium">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>{qaError}</span>
                    </div>
                  )}

                  {/* Cửa sổ đưa đáp án (AI Answer Display Window) */}
                  {(qaResponse || askingAi) && (
                    <div className="bg-[var(--bg-card)] rounded-card border border-[var(--border-subtle)] shadow-xs p-4 space-y-3 transition-all">
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[var(--border-subtle)] text-xs">
                        <div className="flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-[var(--semantic-ai)]" />
                          <span className="font-bold text-[var(--text-primary)]">Đáp án từ trợ lý AI</span>
                          {qaResponse && (
                            <>
                              <Badge variant={qaResponse.is_fallback ? 'amber' : 'forest'}>
                                {qaResponse.provider === 'gemini'
                                  ? 'Google Gemini'
                                  : 'Heuristic Engine'}
                              </Badge>
                              {qaResponse.include_smartkho && (
                                <span className="text-xs bg-[var(--bg-linen)] text-[var(--semantic-ai)] border border-[var(--border-subtle)] px-2 py-0.5 rounded-pill font-bold">
                                  #SmartKho
                                </span>
                              )}
                            </>
                          )}
                        </div>

                        {qaResponse && (
                          <div className="flex items-center gap-3 text-[var(--text-muted)] text-xs font-mono">
                            <span>{qaResponse.timestamp}</span>
                            <button
                              type="button"
                              onClick={handleCopyAnswer}
                              className="inline-flex items-center gap-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] font-medium cursor-pointer transition-colors"
                              title="Sao chép câu trả lời"
                            >
                              {copied ? (
                                <>
                                  <Check className="w-3.5 h-3.5 text-[var(--semantic-success)]" />
                                  <span className="text-[var(--semantic-success)] font-sans">Đã sao chép!</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3.5 h-3.5" />
                                  <span className="font-sans">Sao chép</span>
                                </>
                              )}
                            </button>
                          </div>
                        )}
                      </div>

                      {askingAi ? (
                        <div className="py-6">
                          <Loader
                            variant="page"
                            message={`Trợ lý AI đang phân tích dữ liệu kho kỳ ${month}/${year} và soạn thảo đáp án...`}
                            isAi={true}
                          />
                        </div>
                      ) : (
                        qaResponse && (
                          <div className="space-y-2 text-xs leading-relaxed text-[var(--text-primary)]">
                            <div className="p-2.5 bg-[var(--bg-linen)] rounded-btn text-xs text-[var(--text-primary)] border border-[var(--border-subtle)] font-medium">
                              <strong>Câu hỏi:</strong> {qaResponse.question}
                            </div>
                            <div className="pt-1">
                              {renderFormattedAnswer(qaResponse.answer)}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
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
          <div className="card-warm p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <TrendingUp className="w-4 h-4 text-[var(--wood-accent)] shrink-0" />
              <span className="text-xs font-semibold text-[var(--text-secondary)]">
                Tồn hiện có, Tồn an toàn &amp; Vận tốc xuất trong:
              </span>
              <select
                value={restockDays}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setRestockDays(val);
                  handleFetchRestock(false, val);
                }}
                className="input-warm py-1.5 px-2.5 text-xs w-auto min-w-[120px] font-medium"
              >
                <option value={7}>7 ngày qua</option>
                <option value={14}>14 ngày qua</option>
                <option value={30}>30 ngày qua</option>
                <option value={60}>60 ngày qua</option>
              </select>
            </div>
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => handleFetchRestock(false)}
                disabled={loading}
                className="btn-primary text-xs flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer flex-1 sm:flex-initial shrink-0"
              >
                {loading ? <Loader variant="inline" /> : <Sparkles className="w-4 h-4" />}
                <span>{loading ? 'Đang tải...' : 'Xem gợi ý'}</span>
              </button>
              <button
                onClick={() => handleFetchRestock(true)}
                disabled={loading}
                title="Bỏ qua bản lưu và yêu cầu AI phân tích lại"
                className="btn-secondary text-xs flex items-center justify-center gap-1.5 disabled:opacity-60 cursor-pointer shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Tạo lại</span>
              </button>
            </div>
          </div>

          {loading && !restockData && (
            <div className="card-warm p-8">
              <Loader
                variant="page"
                message="Trợ lý AI đang phân tích tồn kho, tốc độ xuất và tính toán gợi ý nhập hàng..."
                isAi={true}
              />
            </div>
          )}

          {restockData && (
            <div className="space-y-6">
              {/* Provider Info Banner */}
              <div className="p-3.5 bg-[var(--bg-linen)] rounded-card border border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-[var(--text-secondary)]">Động cơ tính toán:</span>
                  <Badge variant={restockData.is_fallback ? 'amber' : 'forest'}>
                    {restockData.is_fallback
                      ? 'Heuristic Fallback Engine (Offline Safe < 50ms)'
                      : 'Google Gemini 3.5 Flash-Lite (Online LLM)'}
                  </Badge>
                  {restockData.is_cached && (
                    <Badge variant="wood">
                      {restockData.cached_at
                        ? `Đã lưu lúc ${restockData.cached_at}`
                        : 'Đã lưu theo khoảng dữ liệu'}
                    </Badge>
                  )}
                </div>
                <span className="text-[var(--text-muted)] font-mono">
                  Phạm vi: {restockData.lookback_days || 30} ngày qua
                  {restockData.start_date && restockData.end_date ? ` (${restockData.start_date} → ${restockData.end_date})` : ''}
                </span>
              </div>

              {/* Executive Summary */}
              <div className="card-warm p-4 border border-[var(--border-subtle)] text-xs text-[var(--text-primary)] leading-relaxed font-medium flex items-center gap-3">
                <Info className="w-5 h-5 text-[var(--semantic-ai)] shrink-0" />
                <span>{restockData.executive_summary}</span>
              </div>

              {/* Suggestions Table */}
              <div className="card-warm overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[var(--bg-linen)] text-[var(--text-secondary)] font-medium border-b border-[var(--border-subtle)]">
                      <tr>
                        <th className="py-3 px-4">Mã SKU</th>
                        <th className="py-3 px-4">Tên hàng hóa</th>
                        <th className="py-3 px-4 text-center">Tồn hiện tại</th>
                        <th className="py-3 px-4 text-center">Tồn an toàn</th>
                        <th className="py-3 px-4 text-center">Vận tốc bán (sp/ngày)</th>
                        <th className="py-3 px-4 text-center font-bold text-[var(--text-primary)]">Đề xuất nhập</th>
                        <th className="py-3 px-4 text-center">Mức ưu tiên</th>
                        <th className="py-3 px-4">Lý do gợi ý từ AI</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-card)]">
                      {restockData.items.length === 0 ? (
                        <tr>
                          <td colSpan="8" className="text-center py-10 text-[var(--text-muted)]">
                            Kho hàng đang ở trạng thái an toàn tuyệt đối. Chưa cần bổ sung mặt hàng nào!
                          </td>
                        </tr>
                      ) : (
                        restockData.items.map((it) => (
                          <tr key={it.product_id} className="hover:bg-[var(--bg-linen)]/60 transition-colors">
                            <td className="py-3.5 px-4 font-mono font-semibold text-[var(--text-primary)]">{it.product_code}</td>
                            <td className="py-3.5 px-4 font-medium text-[var(--text-primary)]">{it.product_name}</td>
                            <td className="py-3.5 px-4 text-center font-mono font-bold text-[var(--semantic-alert)]">{it.current_stock}</td>
                            <td className="py-3.5 px-4 text-center font-mono text-[var(--text-secondary)]">{it.min_stock}</td>
                            <td className="py-3.5 px-4 text-center font-mono text-[var(--text-secondary)]">{it.daily_velocity}</td>
                            <td className="py-3.5 px-4 text-center font-mono">
                              <span className="font-bold text-[var(--semantic-ai)] bg-[var(--bg-linen)] px-2.5 py-1 rounded-btn border border-[var(--border-subtle)]">
                                +{it.suggested_quantity}
                              </span>
                            </td>
                            <td className="py-3.5 px-4 text-center">
                              <Badge
                                variant={
                                  it.priority === 'HIGH'
                                    ? 'alert'
                                    : it.priority === 'MEDIUM'
                                    ? 'amber'
                                    : 'wood'
                                }
                              >
                                {it.priority === 'HIGH' ? 'Khẩn cấp (HIGH)' : it.priority === 'MEDIUM' ? 'Cần nhập (MED)' : 'Thấp (LOW)'}
                              </Badge>
                            </td>
                            <td className="py-3.5 px-4 text-[var(--text-secondary)] max-w-sm leading-relaxed">{it.reason}</td>
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
          <div className="card-warm p-3.5 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2.5">
              <ShieldAlert className="w-4 h-4 text-[var(--semantic-alert)] shrink-0" />
              <span className="text-xs font-semibold text-[var(--text-secondary)]">
                Quét xuất tăng vọt (&gt;200%) &amp; Hàng tồn kho chết trong:
              </span>
              <select
                value={anomalyDays}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  setAnomalyDays(val);
                  handleFetchAnomalies(false, val);
                }}
                className="input-warm py-1.5 px-2.5 text-xs w-auto min-w-[120px] font-medium"
              >
                <option value={7}>7 ngày qua</option>
                <option value={14}>14 ngày qua</option>
                <option value={30}>30 ngày qua</option>
                <option value={60}>60 ngày qua</option>
              </select>
            </div>
            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              <button
                onClick={() => handleFetchAnomalies(false)}
                disabled={loading}
                className="btn-primary text-xs flex items-center justify-center gap-2 disabled:opacity-60 cursor-pointer flex-1 sm:flex-initial shrink-0"
              >
                {loading ? <Loader variant="inline" /> : <Zap className="w-4 h-4" />}
                <span>{loading ? 'Đang tải...' : 'Xem cảnh báo'}</span>
              </button>
              <button
                onClick={() => handleFetchAnomalies(true)}
                disabled={loading}
                title="Bỏ qua bản lưu và quét lại bằng AI"
                className="btn-outline text-[var(--semantic-alert)] border-[var(--semantic-alert-border)] hover:bg-[var(--semantic-alert-bg)] text-xs flex items-center justify-center gap-1.5 disabled:opacity-60 cursor-pointer shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>Tạo lại</span>
              </button>
            </div>
          </div>

          {loading && !anomalyData && (
            <div className="card-warm p-8">
              <Loader
                variant="page"
                message="Trợ lý AI đang quét phát hiện biến động bất thường và hàng tồn kho đọng..."
                isAi={true}
              />
            </div>
          )}

          {anomalyData && (
            <div className="space-y-6">
              {/* Provider Info Banner */}
              <div className="p-3.5 bg-[var(--bg-linen)] rounded-card border border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-[var(--text-secondary)]">Động cơ tính toán:</span>
                  <Badge variant={anomalyData.is_fallback ? 'amber' : 'forest'}>
                    {anomalyData.is_fallback
                      ? 'Heuristic Fallback Engine (Offline Safe < 50ms)'
                      : 'Google Gemini 3.5 Flash-Lite (Online LLM)'}
                  </Badge>
                  {anomalyData.is_cached && (
                    <Badge variant="wood">
                      {anomalyData.cached_at
                        ? `Đã lưu lúc ${anomalyData.cached_at}`
                        : 'Đã lưu theo khoảng dữ liệu'}
                    </Badge>
                  )}
                </div>
                <span className="text-[var(--text-muted)] font-mono">
                  Phạm vi: {anomalyData.lookback_days || 30} ngày qua
                  {anomalyData.start_date && anomalyData.end_date ? ` (${anomalyData.start_date} → ${anomalyData.end_date})` : ''}
                </span>
              </div>

              <div className="p-4 rounded-card border border-[var(--semantic-alert-border)] bg-[var(--semantic-alert-bg)] text-xs text-[var(--semantic-alert)] leading-relaxed font-medium flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 shrink-0" />
                <span>{anomalyData.executive_summary}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {anomalyData.anomalies.length === 0 ? (
                  <div className="md:col-span-2 card-warm p-12 text-center text-[var(--text-muted)] text-xs">
                    Kho vận đang vận hành ổn định! Không ghi nhận đột biến hay hàng ứ đọng bất thường.
                  </div>
                ) : (
                  anomalyData.anomalies.map((ano, idx) => {
                    const isSurge = ano.anomaly_type === 'SURGE_EXPORT';
                    return (
                      <div
                        key={idx}
                        className={`p-5 rounded-card border shadow-xs space-y-3 transition-all ${
                          isSurge
                            ? 'bg-[var(--semantic-alert)]/5 border-[var(--semantic-alert)]/30'
                            : 'card-warm border-[var(--border-subtle)]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {isSurge ? (
                              <Flame className="w-5 h-5 text-[var(--semantic-alert)]" />
                            ) : (
                              <Archive className="w-5 h-5 text-[var(--wood-accent)]" />
                            )}
                            <h4 className="font-bold font-serif text-[var(--text-primary)] text-sm">{ano.product_name}</h4>
                          </div>
                          <Badge variant={isSurge ? 'alert' : 'inactive'}>
                            {isSurge ? 'Xuất tăng đột biến' : 'Hàng tồn lâu (>30 ngày)'}
                          </Badge>
                        </div>

                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed font-sans">{ano.description}</p>

                        <div className="p-3 bg-[var(--bg-card)] rounded-btn border border-[var(--border-subtle)] text-xs">
                          <span className="font-semibold text-[var(--text-primary)] block mb-1 inline-flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-[var(--semantic-ai)]" />
                            Đề xuất hành động từ AI:
                          </span>
                          <span className="text-[var(--text-secondary)]">{ano.suggested_action}</span>
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

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="card-warm p-8 text-center space-y-4 max-w-xl mx-auto my-8 border-rust-200 bg-rust-50/40">
          <div className="w-12 h-12 rounded-full bg-rust-100 flex items-center justify-center mx-auto text-rust-600">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold font-serif text-wood-950">
            Đã xảy ra sự cố khi tải giao diện
          </h3>
          <p className="text-xs text-charcoal/70 leading-relaxed font-sans max-w-md mx-auto">
            {this.state.error?.message || 'Có lỗi không xác định xảy ra trong quá trình kết xuất dữ liệu.'}
          </p>
          <div className="pt-2">
            <button
              onClick={this.handleReset}
              className="btn-secondary text-xs inline-flex items-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Thử lại giao diện</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

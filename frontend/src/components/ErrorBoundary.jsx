import { Component } from 'react';

export default class ErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="center-screen">
        <div className="glass pad narrow">
          <h2>Something broke on this page</h2>
          <p className="muted">Reload to continue. If it keeps happening, your last action was not lost — it is saved in task history.</p>
          <button className="btn primary" onClick={() => window.location.reload()}>Reload page</button>
        </div>
      </div>
    );
  }
}

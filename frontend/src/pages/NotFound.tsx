import React from "react";
import { Link } from "react-router-dom";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="py-16 text-center">
      <h1 className="text-4xl font-bold font-display text-slate-900">404</h1>
      <p className="mt-2 text-slate-600">Page not found.</p>
      <div className="mt-6">
        <Link
          to="/"
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-teal-600 hover:bg-teal-700"
        >
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
};

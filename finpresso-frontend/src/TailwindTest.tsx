// src/TailwindTest.tsx
import React from 'react';

export default function TailwindTest() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-pink-500">
      <button className="px-6 py-3 bg-white text-indigo-600 font-bold rounded-lg shadow-lg hover:bg-indigo-50 transition">
        🎉 Tailwind Works!
      </button>
    </div>
  );
}


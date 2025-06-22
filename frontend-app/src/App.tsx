import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './pages/Auth';
import Chat from './pages/Chat';
import Documents from './pages/Documents';
import DocumentCollectionDetail from './pages/DocumentCollectionDetail';
import Models from './pages/Models';
import TestCollections from './pages/TestCollections';
import SimpleTest from './pages/SimpleTest';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/auth" element={<Auth />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/collections/:id" element={<DocumentCollectionDetail />} />
        <Route path="/models" element={<Models />} />
        <Route path="/test-collections" element={<TestCollections />} />
        <Route path="/simple-test" element={<SimpleTest />} />
        <Route path="/" element={<Navigate replace to="/auth" />} />
      </Routes>
    </Router>
  );
};

export default App;
import React, { createContext, useContext, useState, useEffect } from 'react';

type ViewMode = 'student' | 'admin';

interface ViewModeContextType {
  viewMode: ViewMode;
  toggleViewMode: () => void;
  setViewMode: (mode: ViewMode) => void;
  isSubmitModalOpen: boolean;
  openSubmitModal: () => void;
  closeSubmitModal: () => void;
}

const ViewModeContext = createContext<ViewModeContextType | undefined>(undefined);

export const ViewModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [viewMode, setViewModeState] = useState<ViewMode>(() => {
    const saved = localStorage.getItem('campusvoice_view_mode');
    return saved === 'admin' ? 'admin' : 'student';
  });

  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem('campusvoice_view_mode', viewMode);
  }, [viewMode]);

  const toggleViewMode = () => {
    setViewModeState((prev) => (prev === 'student' ? 'admin' : 'student'));
  };

  const setViewMode = (mode: ViewMode) => {
    setViewModeState(mode);
  };

  const openSubmitModal = () => setIsSubmitModalOpen(true);
  const closeSubmitModal = () => setIsSubmitModalOpen(false);

  return (
    <ViewModeContext.Provider
      value={{
        viewMode,
        toggleViewMode,
        setViewMode,
        isSubmitModalOpen,
        openSubmitModal,
        closeSubmitModal,
      }}
    >
      {children}
    </ViewModeContext.Provider>
  );
};

export const useViewMode = (): ViewModeContextType => {
  const context = useContext(ViewModeContext);
  if (!context) {
    throw new Error('useViewMode must be used within a ViewModeProvider');
  }
  return context;
};


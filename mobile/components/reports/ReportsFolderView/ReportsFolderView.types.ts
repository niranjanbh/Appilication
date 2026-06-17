export interface ReportFolder {
  id: string;
  name: string;
  fileCount: number;
  iconName: string;
}

export interface ReportFile {
  id: string;
  name: string;
  fileType: 'pdf' | 'image' | 'other';
  uploadedAt: string;
  /** Doctor-set review status — undefined if not yet reviewed. */
  reviewStatus?: string;
  reviewerName?: string;
}

export interface ReportsFolderViewProps {
  folders: ReportFolder[];
  recentFiles: ReportFile[];
  onUpload: () => void;
  onDownload: (file: ReportFile) => void;
  onDelete: (file: ReportFile) => void;
  onOpenFolder: (folder: ReportFolder) => void;
  onOpenFile: (file: ReportFile) => void;
}

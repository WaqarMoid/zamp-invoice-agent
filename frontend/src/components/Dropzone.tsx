import React, { useRef, useState } from "react";
import { Upload } from "lucide-react";

export interface DropzoneProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSizeBytes?: number;
  className?: string;
}

export const Dropzone: React.FC<DropzoneProps> = ({
  onFileSelect,
  accept = "application/pdf,image/png,image/jpeg",
  maxSizeBytes = 10 * 1024 * 1024, // 10 MB
  className = "",
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndPass = (file: File) => {
    setError(null);
    if (file.size > maxSizeBytes) {
      setError("File is too large: maximum allowed size is 10 MB.");
      return;
    }
    const validMimes = ["application/pdf", "image/png", "image/jpeg"];
    if (!validMimes.includes(file.type) && !file.name.match(/\.(pdf|png|jpe?g)$/i)) {
      setError("Unsupported file format: only PDF, PNG or JPG are accepted.");
      return;
    }
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndPass(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndPass(e.target.files[0]);
    }
  };

  return (
    <div className={`w-full ${className}`}>
      <div
        onClick={() => inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`h-[220px] rounded-[10px] border-[1.5px] border-dashed flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-colors select-none ${
          isDragOver
            ? "border-[var(--ink)] bg-[var(--surface-sunken)]"
            : "border-[var(--line-strong)] bg-[var(--surface)] hover:bg-[var(--surface-sunken)]"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
        />

        <div className="w-10 h-10 rounded-full bg-[var(--surface-sunken)] border border-[var(--line)] flex items-center justify-center text-[var(--ink-2)] mb-3">
          <Upload size={18} strokeWidth={1.5} />
        </div>

        <p className="font-sans font-medium text-[15px] leading-[22px] text-[var(--ink)] m-0">
          Drop an invoice PDF or image
        </p>
        <p className="font-sans text-[13px] leading-[20px] text-[var(--ink-3)] mt-1 m-0">
          or browse · PDF, PNG, JPG up to 10 MB
        </p>

        {error && (
          <p className="font-sans text-[13px] leading-[18px] text-[var(--reject)] mt-3 m-0 font-medium">
            {error}
          </p>
        )}
      </div>
    </div>
  );
};

'use client';

import { useRef } from 'react';
import Editor, { OnMount } from '@monaco-editor/react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  readOnly?: boolean;
  height?: string;
  ariaLabel?: string;
}

export default function CodeEditor({
  value,
  onChange,
  language = 'json',
  readOnly = false,
  height = '400px',
  ariaLabel,
}: CodeEditorProps) {
  const editorRef = useRef<Parameters<OnMount>[0] | null>(null);

  const handleEditorDidMount: OnMount = (editor) => {
    editorRef.current = editor;
  };

  const handleChange = (newValue: string | undefined) => {
    onChange(newValue ?? '');
  };

  return (
    <div className="rounded-lg overflow-hidden border border-gray-700">
      <Editor
        height={height}
        defaultLanguage={language}
        value={value}
        onChange={handleChange}
        onMount={handleEditorDidMount}
        theme="vs-dark"
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          wordWrap: 'on',
          padding: { top: 16, bottom: 16 },
        }}
        aria-label={ariaLabel}
      />
    </div>
  );
}

import React, { useState, useRef } from 'react';
import { Mic, Square, Upload, Loader2 } from 'lucide-react';
import axios from 'axios';

const AudioRecorder = ({ onUploadComplete }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const recordingIntervalRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      chunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        chunksRef.current.push(event.data);
      };
      
      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
      
      // Start timer
      const startTime = Date.now();
      recordingIntervalRef.current = setInterval(() => {
        setRecordingTime(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
      
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Error accessing microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      if (recordingIntervalRef.current) {
        clearInterval(recordingIntervalRef.current);
        recordingIntervalRef.current = null;
      }
    }
  };

  const uploadAudio = async () => {
    if (!audioBlob) return;
    
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');
      
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(progress);
        },
      });
      
      if (response.data.conversation_id) {
        onUploadComplete(response.data);
        setAudioBlob(null);
        setRecordingTime(0);
        setUploadProgress(0);
      }
      
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const resetRecording = () => {
    setAudioBlob(null);
    setRecordingTime(0);
    setUploadProgress(0);
  };

  return (
    <div className="audio-recorder text-white">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold mb-2">Record Your Conversation</h2>
        <p className="text-blue-100">Click the microphone to start recording</p>
      </div>
      
      <div className="flex flex-col items-center space-y-6">
        {/* Recording Controls */}
        <div className="flex items-center space-x-4">
          {!isRecording && !audioBlob && (
            <button
              onClick={startRecording}
              className="record-button bg-red-500 hover:bg-red-600 p-6 rounded-full shadow-lg"
              disabled={isUploading}
            >
              <Mic size={32} />
            </button>
          )}
          
          {isRecording && (
            <button
              onClick={stopRecording}
              className="record-button recording bg-red-600 p-6 rounded-full shadow-lg"
            >
              <Square size={32} />
            </button>
          )}
          
          {audioBlob && !isRecording && (
            <button
              onClick={uploadAudio}
              className="record-button bg-green-500 hover:bg-green-600 p-6 rounded-full shadow-lg"
              disabled={isUploading}
            >
              {isUploading ? <Loader2 size={32} className="animate-spin" /> : <Upload size={32} />}
            </button>
          )}
        </div>
        
        {/* Recording Status */}
        {isRecording && (
          <div className="text-center">
            <div className="text-2xl font-mono font-bold text-red-200">
              {formatTime(recordingTime)}
            </div>
            <div className="text-red-100">Recording...</div>
          </div>
        )}
        
        {/* Upload Progress */}
        {isUploading && (
          <div className="w-full max-w-md">
            <div className="flex justify-between text-sm mb-2">
              <span>Uploading...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}
        
        {/* Audio Preview */}
        {audioBlob && !isRecording && (
          <div className="text-center">
            <audio controls className="mb-4">
              <source src={URL.createObjectURL(audioBlob)} type="audio/wav" />
              Your browser does not support the audio element.
            </audio>
            <div className="space-x-2">
              <button
                onClick={resetRecording}
                className="px-4 py-2 bg-gray-500 hover:bg-gray-600 rounded-lg text-sm"
              >
                Record Again
              </button>
            </div>
          </div>
        )}
        
        {/* Instructions */}
        <div className="text-center text-blue-100 text-sm max-w-md">
          <p>• Ensure good audio quality in a quiet environment</p>
          <p>• Speak clearly for better transcription accuracy</p>
          <p>• Processing may take a few minutes for longer recordings</p>
        </div>
      </div>
    </div>
  );
};

export default AudioRecorder;

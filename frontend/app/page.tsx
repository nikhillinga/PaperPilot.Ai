import UploadForm from "./components/UploadForm";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-14rem)] py-8">
      <UploadForm />
    </div>
  );
}

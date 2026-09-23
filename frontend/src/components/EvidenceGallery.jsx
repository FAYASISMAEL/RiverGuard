import { useEffect, useRef, useState } from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
export default function EvidenceGallery({
  images = [],
  removable = false,
  onRemove,
}) {
  const [active, setActive] = useState(null),
    dialog = useRef(null);
  useEffect(() => {
    if (active !== null) dialog.current?.showModal();
    else dialog.current?.close();
  }, [active]);
  if (!images.length) return null;
  return (
    <>
      <div className="evidence-grid">
        {images.map((image, i) => (
          <div className="evidence-tile" key={image.id || image.src}>
            <button
              type="button"
              className="evidence-open"
              onClick={() => setActive(i)}
              aria-label={"View evidence image " + (i + 1)}
            >
              <img src={image.src} alt={"Evidence image " + (i + 1)} />
            </button>
            <div>
              <span>{image.name || "Evidence " + (i + 1)}</span>
              {removable && (
                <button
                  type="button"
                  onClick={() => onRemove(image.id)}
                  aria-label={"Remove image " + (i + 1)}
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <dialog
        ref={dialog}
        className="lightbox"
        onCancel={() => setActive(null)}
        onClick={(e) => {
          if (e.target === dialog.current) setActive(null);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") setActive((active + 1) % images.length);
          if (e.key === "ArrowLeft")
            setActive((active + images.length - 1) % images.length);
        }}
      >
        <div className="lightbox-controls">
          <span>
            Evidence {active !== null ? active + 1 : 0} / {images.length}
          </span>
          <button
            type="button"
            aria-label="Close image viewer"
            onClick={() => setActive(null)}
          >
            <X />
          </button>
        </div>
        {active !== null && images[active] && (
          <img
            src={images[active].src}
            alt={"Evidence image " + (active + 1) + " enlarged"}
          />
        )}
        <div className="lightbox-controls">
          <button
            type="button"
            disabled={images.length < 2}
            onClick={() =>
              setActive((active + images.length - 1) % images.length)
            }
          >
            <ChevronLeft />
            Previous
          </button>
          <button
            type="button"
            disabled={images.length < 2}
            onClick={() => setActive((active + 1) % images.length)}
          >
            Next
            <ChevronRight />
          </button>
        </div>
      </dialog>
    </>
  );
}

import React, { useState } from 'react';
import { X, Car, ShieldAlert, CheckCircle2, Search, Download, ExternalLink, Camera } from 'lucide-react';
import { AnalyzedVehicleSummary } from '../utils/reidEngine';

interface VehicleInventoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  vehicles: AnalyzedVehicleSummary[];
  selectedVehicleId: string | null;
  onSelectVehicle: (id: string) => void;
  anprPlateMatch: string;
}

export const VehicleInventoryModal: React.FC<VehicleInventoryModalProps> = ({
  isOpen,
  onClose,
  vehicles,
  selectedVehicleId,
  onSelectVehicle,
  anprPlateMatch,
}) => {
  const [filterQuery, setFilterQuery] = useState('');
  const [cameraFilter, setCameraFilter] = useState<'all' | 'cam-01' | 'cam-02' | 'cam-03'>('all');

  if (!isOpen) return null;

  const filtered = vehicles.filter((v) => {
    const matchesCam = cameraFilter === 'all' || v.cameraId === cameraFilter;
    const q = filterQuery.toLowerCase();
    const matchesQuery =
      !q ||
      v.id.toLowerCase().includes(q) ||
      v.makeModel.toLowerCase().includes(q) ||
      v.licensePlate.toLowerCase().includes(q) ||
      v.cameraName.toLowerCase().includes(q) ||
      v.bodyType.toLowerCase().includes(q);
    return matchesCam && matchesQuery;
  });

  const handleExportJson = () => {
    const blob = new Blob([JSON.stringify(vehicles, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `eaglevision-detected-vehicles-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="vehicle-inventory-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-3 sm:p-5"
    >
      <div className="w-full max-w-5xl max-h-[90vh] flex flex-col bg-[#0c1017] border border-slate-700 rounded-sm shadow-2xl overflow-hidden font-mono">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#080a0f] border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <Car className="w-4 h-4 text-cyan-400" />
            <div>
              <h2
                id="vehicle-inventory-title"
                className="text-xs sm:text-sm font-bold font-display tracking-wider text-slate-100 uppercase"
              >
                EAGLEVISION™ // DETECTED VEHICLES &amp; VIDEO FLEET INVENTORY
              </h2>
              <p className="text-[10px] text-slate-400 font-sans">
                Real-time extraction of Car Make/Model, License Plate (ANPR), and Kinematics from uploaded CCTV feeds
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close inventory modal"
            className="p-1 text-slate-400 hover:text-slate-100 rounded transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tactical Key Metrics Banner */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 px-4 py-2.5 bg-[#0a0e16] border-b border-slate-800/90 text-[10px] tabular-nums">
          <div className="p-2 bg-[#080a0f] border border-slate-800 rounded-[2px]">
            <span className="text-slate-400 block text-[9px]">TOTAL VEHICLES EXTRACTED</span>
            <span className="text-sm font-bold text-slate-100">{vehicles.length} VEHICLES</span>
          </div>
          <div className="p-2 bg-[#080a0f] border border-cyan-500/40 rounded-[2px]">
            <span className="text-cyan-400 block text-[9px]">PRIMARY TARGET (ANPR LOCK)</span>
            <span className="text-sm font-bold text-cyan-300">{vehicles.length > 0 ? `ID-${vehicles[0].id}` : 'NONE'}</span>
          </div>
          <div className="p-2 bg-[#080a0f] border border-emerald-500/40 rounded-[2px]">
            <span className="text-emerald-400 block text-[9px]">CROSS-CAMERA MATCH</span>
            <span className="text-[11px] font-bold text-emerald-300 truncate block">{anprPlateMatch || 'AWAITING SCAN'}</span>
          </div>
          <div className="p-2 bg-[#080a0f] border border-red-500/40 rounded-[2px]">
            <span className="text-red-400 block text-[9px]">ANOMALY ALERTS DETECTED</span>
            <span className="text-sm font-bold text-red-300">
              {vehicles.filter((v) => v.isAnomaly).length} INCIDENT
            </span>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 bg-[#080a0f]/90 border-b border-slate-800 text-[11px]">
          <div className="flex items-center gap-2 flex-1 min-w-[240px]">
            <div className="relative flex-1">
              <Search className="w-3 h-3 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                placeholder="Filter by Make, Model, Plate, ID, or Camera..."
                className="w-full pl-7 pr-2.5 py-1 bg-[#0c1017] border border-slate-700 rounded-[2px] text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>
            {filterQuery && (
              <button
                type="button"
                onClick={() => setFilterQuery('')}
                className="text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                [Clear]
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0 text-[10px]">
            <span className="text-slate-400">Camera:</span>
            <select
              value={cameraFilter}
              onChange={(e) => setCameraFilter(e.target.value as any)}
              className="px-2 py-1 bg-[#0c1017] border border-slate-700 rounded-[2px] text-slate-200 focus:outline-none focus:border-cyan-500 cursor-pointer"
            >
              <option value="all">All Cameras (3)</option>
              <option value="cam-01">CAM-01 (Entry)</option>
              <option value="cam-02">CAM-02 (Exit / Highway)</option>
              <option value="cam-03">CAM-03 (Highway South)</option>
            </select>
            <button
              type="button"
              onClick={handleExportJson}
              className="ml-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 rounded-[2px] flex items-center gap-1 transition-colors cursor-pointer"
            >
              <Download className="w-3 h-3" />
              <span>EXPORT JSON</span>
            </button>
          </div>
        </div>

        {/* Vehicles Table */}
        <div className="flex-1 overflow-y-auto p-4">
          <div className="overflow-x-auto border border-slate-800 rounded-[2px]">
            <table className="w-full text-left text-[11px] border-collapse">
              <thead>
                <tr className="bg-[#080a0f] border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                  <th className="py-2 px-3">Vehicle / Crop</th>
                  <th className="py-2 px-3">Brand &amp; Make / Model</th>
                  <th className="py-2 px-3">License Plate (ANPR)</th>
                  <th className="py-2 px-3">Body &amp; Color</th>
                  <th className="py-2 px-3">Camera Point</th>
                  <th className="py-2 px-3">Speed &amp; Delta</th>
                  <th className="py-2 px-3">Forensic Status</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {filtered.map((v) => {
                  const isSelected = selectedVehicleId === v.id;
                  return (
                    <tr
                      key={`${v.id}-${v.cameraId}`}
                      className={`hover:bg-slate-900/60 transition-colors ${
                        isSelected ? 'bg-cyan-950/30' : ''
                      }`}
                    >
                      {/* Vehicle ID & Crop Preview */}
                      <td className="py-2 px-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {v.thumbnailDataUrl ? (
                            <img
                              src={v.thumbnailDataUrl}
                              alt={v.makeModel}
                              className="w-12 h-7 object-cover rounded-[1px] border border-slate-700 shrink-0"
                            />
                          ) : (
                            <div className="w-12 h-7 bg-slate-900 border border-slate-800 flex items-center justify-center rounded-[1px] shrink-0">
                              <Car className="w-3.5 h-3.5 text-slate-500" />
                            </div>
                          )}
                          <div>
                            <span
                              className={`px-1.5 py-0.5 rounded-[2px] text-[9.5px] font-bold ${
                                v.cosineSim >= 0.85
                                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              ID-{v.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Make & Model */}
                      <td className="py-2 px-3">
                        <span className="font-semibold text-slate-100">{v.makeModel}</span>
                      </td>

                      {/* License Plate (ANPR) */}
                      <td className="py-2 px-3 whitespace-nowrap">
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-[#080a0f] border border-slate-700 rounded-[2px]">
                          <span className="w-1.5 h-3 bg-blue-600 rounded-[1px]" />
                          <span className="font-bold text-slate-100 tracking-wider">
                            {v.licensePlate}
                          </span>
                        </div>
                        <span className="ml-1.5 text-[9px] text-emerald-400 font-semibold tabular-nums">
                          {(v.plateConfidence * 100).toFixed(0)}% OCR
                        </span>
                      </td>

                      {/* Body & Color */}
                      <td className="py-2 px-3 whitespace-nowrap">
                        <span className="text-slate-300">{v.bodyType}</span>
                        <span className="text-slate-500 block text-[9.5px]">{v.color}</span>
                      </td>

                      {/* Camera Point */}
                      <td className="py-2 px-3 whitespace-nowrap">
                        <span className="text-slate-300">{v.cameraName}</span>
                        <span className="text-slate-500 block text-[9.5px] tabular-nums">
                          {v.timestamp} UTC
                        </span>
                      </td>

                      {/* Speed & Delta */}
                      <td className="py-2 px-3 whitespace-nowrap tabular-nums">
                        <span className="text-slate-200 font-semibold">{v.speedKmh} km/h</span>
                        {v.speedDeltaKmh < 0 ? (
                          <span className="text-red-400 font-bold block text-[9.5px]">
                            {v.speedDeltaKmh} km/h² (Brake)
                          </span>
                        ) : (
                          <span className="text-slate-500 block text-[9.5px]">Cruise</span>
                        )}
                      </td>

                      {/* Forensic Status */}
                      <td className="py-2 px-3">
                        {v.isAnomaly ? (
                          <span className="inline-flex items-center gap-1 text-[9px] font-bold text-red-400 bg-red-950/60 border border-red-500/40 px-1.5 py-0.5 rounded-[2px]">
                            <ShieldAlert className="w-2.5 h-2.5" />
                            <span>KINEMATIC ANOMALY</span>
                          </span>
                        ) : v.cosineSim >= 0.85 ? (
                          <span className="inline-flex items-center gap-1 text-[9px] font-bold text-emerald-300 bg-emerald-950/60 border border-emerald-500/40 px-1.5 py-0.5 rounded-[2px]">
                            <CheckCircle2 className="w-2.5 h-2.5" />
                            <span>CONFIRMED RE-ID</span>
                          </span>
                        ) : (
                          <span className="text-[9.5px] text-slate-400">{v.status}</span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-2 px-3 text-right whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => {
                            onSelectVehicle(v.id);
                            onClose();
                          }}
                          className={`px-2 py-0.5 text-[9.5px] font-semibold rounded-[2px] transition-colors cursor-pointer ${
                            isSelected
                              ? 'bg-cyan-500 text-slate-950'
                              : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                          }`}
                        >
                          {isSelected ? '[ TRACKING ]' : '[ ISOLATE & TRACK ]'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {filtered.length === 0 && (
            <div className="py-8 text-center text-slate-500 text-xs">
              No vehicles matched filter criteria.
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#080a0f] border-t border-slate-800 text-[10px] text-slate-400">
          <span>
            {filtered.length} of {vehicles.length} vehicles displayed • Real-time ANPR &amp; VLM pipeline
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-[2px] transition-colors cursor-pointer"
          >
            [ CLOSE INVENTORY ]
          </button>
        </div>
      </div>
    </div>
  );
};

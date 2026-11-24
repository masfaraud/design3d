// design3d babylonjs viewer: scene tree panel, selection, visibility, opacity, color and camera tools.
// Called by the page template once the babylonjs scene is built:
//   design3dViewer({scene, camera, canvas, data, meshes, lines, axes});
// - data: babylon_data of the model, whose optional "tree" gives the hierarchy of its primitives
// - meshes, lines: babylonjs meshes in the order of data.meshes and data.lines
// - axes: root node of the axes helper
function design3dViewer(ctx) {
   "use strict";
   var scene = ctx.scene, camera = ctx.camera, data = ctx.data;
   var HIGHLIGHT = new BABYLON.Color3(0.15, 0.3, 0.6);
   var nodes = [];             // every tree node, in display order
   var meshToNode = new Map(); // babylon mesh uniqueId -> deepest node owning it
   var selected = null;

   // ---------------------------------------------------------------- tree model
   function makeNode(name, type, parent) {
      var node = {name: name, type: type, parent: parent, children: [], meshes: [], lines: [],
                  visible: true, expanded: false, row: null, childrenEl: null, checkbox: null};
      nodes.push(node);
      if (parent) parent.children.push(node);
      return node;
   }

   function displayName(name, type, index) {
      return name ? name : type + " " + (index + 1);
   }

   function addMesh(node, mesh) {
      node.meshes.push(mesh);
      meshToNode.set(mesh.uniqueId, node);
      // Shells displayed with merge_meshes=False: one child mesh per face
      var faces = mesh.getChildMeshes(true);
      if (faces.length && node.children.length === 0) {
         faces.forEach(function (face, i) {
            addMesh(makeNode(displayName(face.name, "Face", i), "Face", node), face);
         });
      }
   }

   function buildFromTree(items, parent) {
      items.forEach(function (item, i) {
         var node = makeNode(displayName(item.name, item.type, i), item.type, parent);
         item.meshes.forEach(function (index) { if (ctx.meshes[index]) addMesh(node, ctx.meshes[index]); });
         item.lines.forEach(function (index) { if (ctx.lines[index]) node.lines.push(ctx.lines[index]); });
         buildFromTree(item.children || [], node);
      });
   }

   var root = makeNode(data.title || "Model", "Model", null);
   root.expanded = true;
   if (data.tree) {
      buildFromTree(data.tree, root);
   } else {
      // Data without hierarchy (moving volume models...): one node per mesh and line
      ctx.meshes.forEach(function (mesh, i) { addMesh(makeNode(displayName(mesh.name, "Mesh", i), "Mesh", root), mesh); });
      ctx.lines.forEach(function (line, i) { makeNode("Line " + (i + 1), "Line", root).lines.push(line); });
   }
   if (root.children.length === 1) root.children[0].expanded = true;

   // Original appearance, to reset nodes
   ctx.meshes.forEach(function (mesh) {
      [mesh].concat(mesh.getChildMeshes(false)).forEach(function (m) {
         if (!m.material) return;
         m.metadata = m.metadata || {};
         m.metadata.d3d = {color: m.material.diffuseColor.clone(), alpha: m.material.alpha,
                           edgesAlpha: m.edgesColor ? m.edgesColor.a : 1};
      });
   });

   function walk(node, fn) {
      fn(node);
      node.children.forEach(function (child) { walk(child, fn); });
   }

   // Meshes and lines of a node and its descendants
   function nodeMeshes(node) {
      var result = new Set();
      walk(node, function (n) {
         n.meshes.forEach(function (m) {
            result.add(m);
            m.getChildMeshes(false).forEach(function (c) { result.add(c); });
         });
      });
      return Array.from(result);
   }

   function nodeLines(node) {
      var result = [];
      walk(node, function (n) { result.push.apply(result, n.lines); });
      return result;
   }

   function geometryMeshes(node) {
      return nodeMeshes(node).filter(function (m) { return m.getTotalVertices() > 0; });
   }

   // ---------------------------------------------------------------- DOM
   function el(tag, attrs, text) {
      var e = document.createElement(tag);
      Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); });
      if (text !== undefined) e.textContent = text;
      return e;
   }

   if (data.dark_mode) document.body.classList.add("d3d-dark");
   var panel = el("aside", {id: "d3d-panel"});
   var header = el("header");
   header.appendChild(el("div", {id: "d3d-title", title: root.name}, root.name));
   var search = el("input", {id: "d3d-search", type: "search", placeholder: "Filter by name..."});
   header.appendChild(search);
   var treeEl = el("div", {id: "d3d-tree", tabindex: "0"});
   var props = el("section", {id: "d3d-props", hidden: ""});
   panel.appendChild(header);
   panel.appendChild(treeEl);
   panel.appendChild(props);
   document.body.insertBefore(panel, ctx.canvas);

   function nodeColor(node) {
      var meshes = geometryMeshes(node);
      return meshes.length && meshes[0].material ? meshes[0].material.diffuseColor.toHexString() : null;
   }

   function renderRow(node, depth) {
      var row = el("div", {"class": "d3d-row"});
      row.style.paddingLeft = (4 + 14 * depth) + "px";
      var caret = el("span", {"class": "d3d-caret"}, node.children.length ? (node.expanded ? "▾" : "▸") : "");
      var checkbox = el("input", {type: "checkbox", title: "Show / hide (H)"});
      checkbox.checked = node.visible;
      row.appendChild(caret);
      row.appendChild(checkbox);
      var color = nodeColor(node);
      if (color && node.children.length === 0) {
         var swatch = el("span", {"class": "d3d-swatch"});
         swatch.style.background = color;
         row.appendChild(swatch);
         node.swatch = swatch;
      }
      row.appendChild(el("span", {"class": "d3d-label", title: node.name}, node.name));
      if (node.type !== node.name && node.parent) row.appendChild(el("span", {"class": "d3d-type"}, node.type));
      caret.addEventListener("click", function (e) { e.stopPropagation(); toggleExpanded(node); });
      checkbox.addEventListener("click", function (e) { e.stopPropagation(); setVisible(node, checkbox.checked); });
      row.addEventListener("click", function () { select(node); });
      row.addEventListener("dblclick", function () { focus(node); });
      node.row = row;
      node.caret = caret;
      node.checkbox = checkbox;
      updateRowState(node);
      return row;
   }

   // Children rows are only built when a node is expanded: shells may have thousands of faces
   function renderChildren(node, depth) {
      var container = el("div", {"class": "d3d-children"});
      node.childrenEl = container;
      node.childrenDepth = depth;
      node.rendered = node.expanded;
      if (!node.expanded) {
         container.classList.add("d3d-collapsed");
         return container;
      }
      node.children.forEach(function (child) {
         if (child.filteredOut) return;
         container.appendChild(renderRow(child, depth + 1));
         if (child.children.length) container.appendChild(renderChildren(child, depth + 1));
      });
      return container;
   }

   function renderTree() {
      nodes.forEach(function (n) { n.row = null; n.checkbox = null; n.childrenEl = null; n.swatch = null; });
      treeEl.textContent = "";
      treeEl.appendChild(renderRow(root, 0));
      treeEl.appendChild(renderChildren(root, 0));
      if (selected && selected.row) selected.row.classList.add("d3d-selected");
   }

   function toggleExpanded(node, expanded) {
      if (!node.children.length) return;
      node.expanded = expanded === undefined ? !node.expanded : expanded;
      if (!node.childrenEl) return;
      if (node.expanded && !node.rendered) {
         var previous = node.childrenEl;
         previous.replaceWith(renderChildren(node, node.childrenDepth));
      }
      node.childrenEl.classList.toggle("d3d-collapsed", !node.expanded);
      node.caret.textContent = node.expanded ? "▾" : "▸";
   }

   function reveal(node) {
      var ancestors = [];
      for (var p = node.parent; p; p = p.parent) ancestors.unshift(p);
      ancestors.forEach(function (a) { toggleExpanded(a, true); });
      if (node.row) node.row.scrollIntoView({block: "nearest"});
   }

   // Checkbox state: checked, unchecked or indeterminate when descendants are mixed
   function updateRowState(node) {
      if (!node.checkbox) return;
      var shown = 0, total = 0;
      walk(node, function (n) { if (n.meshes.length || n.lines.length) { total++; if (n.visible) shown++; } });
      node.checkbox.checked = shown > 0;
      node.checkbox.indeterminate = shown > 0 && shown < total;
      node.row.classList.toggle("d3d-hidden", shown === 0);
   }

   function updateAncestorsState(node) {
      for (var n = node; n; n = n.parent) updateRowState(n);
   }

   // ---------------------------------------------------------------- actions
   function setVisible(node, visible) {
      walk(node, function (n) {
         n.visible = visible;
         n.meshes.forEach(function (m) { m.isVisible = visible; });
         n.lines.forEach(function (l) { l.isVisible = visible; });
         updateRowState(n);
      });
      // A shell mesh with face children: the faces follow the shell
      nodeMeshes(node).forEach(function (m) { m.isVisible = visible; });
      updateAncestorsState(node);
      if (node === selected) renderProps();
   }

   function showAll() { setVisible(root, true); }

   function isolate(node) {
      setVisible(root, false);
      setVisible(node, true);
   }

   function setAlpha(node, alpha) {
      nodeMeshes(node).forEach(function (m) {
         if (!m.material) return;
         m.material.alpha = alpha;
         if (m.edgesColor && m.metadata && m.metadata.d3d) m.edgesColor.a = m.metadata.d3d.edgesAlpha * alpha;
      });
   }

   function setColor(node, hex) {
      var color = BABYLON.Color3.FromHexString(hex);
      nodeMeshes(node).forEach(function (m) { if (m.material) m.material.diffuseColor = color.clone(); });
      walk(node, function (n) { if (n.swatch) n.swatch.style.background = hex; });
   }

   function resetAppearance(node) {
      nodeMeshes(node).forEach(function (m) {
         var orig = m.metadata && m.metadata.d3d;
         if (!orig) return;
         m.material.diffuseColor = orig.color.clone();
         m.material.alpha = orig.alpha;
         if (m.edgesColor) m.edgesColor.a = orig.edgesAlpha;
      });
      walk(node, function (n) { if (n.swatch) n.swatch.style.background = nodeColor(n); });
      renderProps();
   }

   function highlight(node, on) {
      if (!node) return;
      nodeMeshes(node).forEach(function (m) {
         if (m.material) m.material.emissiveColor = on ? HIGHLIGHT : BABYLON.Color3.Black();
      });
   }

   function select(node) {
      if (selected) {
         highlight(selected, false);
         if (selected.row) selected.row.classList.remove("d3d-selected");
      }
      selected = node;
      if (node) {
         if (node !== root) highlight(node, true);
         reveal(node);
         if (node.row) node.row.classList.add("d3d-selected");
      }
      renderProps();
   }

   function boundingBox(node, visibleOnly) {
      var min = null, max = null;
      geometryMeshes(node).concat(nodeLines(node)).forEach(function (m) {
         if (visibleOnly && !m.isVisible) return;
         m.computeWorldMatrix(true);
         var box = m.getBoundingInfo().boundingBox;
         min = min ? BABYLON.Vector3.Minimize(min, box.minimumWorld) : box.minimumWorld.clone();
         max = max ? BABYLON.Vector3.Maximize(max, box.maximumWorld) : box.maximumWorld.clone();
      });
      return min ? {min: min, max: max} : null;
   }

   function focus(node) {
      var box = boundingBox(node || root, true) || boundingBox(node || root, false);
      if (!box) return;
      var center = box.min.add(box.max).scale(0.5);
      var radius = Math.max(box.max.subtract(box.min).length() / 2, 1e-6 * data.max_length);
      var direction = camera.position.subtract(camera.target);
      camera.setTarget(center);
      camera.radius = 1.1 * radius / Math.sin(camera.fov / 2);
      if (direction.length() > 0) camera.setPosition(center.add(direction.normalize().scale(camera.radius)));
   }

   // Standard views, the z axis being up
   var VIEWS = {
      "Iso": new BABYLON.Vector3(1, -1, 1),
      "Front": new BABYLON.Vector3(0, -1, 0),
      "Back": new BABYLON.Vector3(0, 1, 0),
      "Left": new BABYLON.Vector3(-1, 0, 0),
      "Right": new BABYLON.Vector3(1, 0, 0),
      "Top": new BABYLON.Vector3(0, -1e-3, 1),
      "Bottom": new BABYLON.Vector3(0, -1e-3, -1)
   };

   function setView(direction) {
      camera.setPosition(camera.target.add(direction.normalize().scale(camera.radius)));
   }

   var edgesShown = true;
   function toggleEdges() {
      edgesShown = !edgesShown;
      scene.meshes.forEach(function (m) { if (m.edgesRenderer) m.edgesRenderer.isEnabled = edgesShown; });
      return edgesShown;
   }

   var wireframe = false;
   function toggleWireframe() {
      wireframe = !wireframe;
      ctx.meshes.forEach(function (mesh) {
         [mesh].concat(mesh.getChildMeshes(false)).forEach(function (m) {
            if (m.material) m.material.wireframe = wireframe;
         });
      });
      return wireframe;
   }

   function toggleAxes() {
      if (!ctx.axes) return false;
      var enabled = !ctx.axes.isEnabled();
      ctx.axes.setEnabled(enabled);
      return enabled;
   }

   function togglePanel() {
      var hidden = document.body.classList.toggle("d3d-panel-hidden");
      ctx.engine.resize();
      return !hidden;
   }

   function toggleInspector() {
      if (scene.debugLayer.isVisible()) {
         scene.debugLayer.hide();
         return false;
      }
      scene.debugLayer.show({embedMode: true});
      return true;
   }

   // ---------------------------------------------------------------- properties of the selection
   function renderProps() {
      props.textContent = "";
      if (!selected) { props.hidden = true; return; }
      props.hidden = false;
      var node = selected;
      props.appendChild(el("div", {"class": "d3d-prop-name", title: node.name}, node.name));
      var info = [node.type];
      var triangles = geometryMeshes(node).reduce(function (sum, m) { return sum + m.getTotalIndices() / 3; }, 0);
      if (triangles) info.push(triangles + " triangles");
      var box = boundingBox(node, false);
      if (box) {
         var size = box.max.subtract(box.min);
         info.push("size " + [size.x, size.y, size.z].map(function (v) { return +v.toPrecision(4); }).join(" × "));
      }
      props.appendChild(el("div", {"class": "d3d-prop-info"}, info.join(" · ")));

      var meshes = geometryMeshes(node);
      if (meshes.length && meshes[0].material) {
         var alphaLabel = el("label");
         alphaLabel.appendChild(el("span", {}, "Opacity"));
         var slider = el("input", {type: "range", min: "0.05", max: "1", step: "0.05"});
         slider.value = meshes[0].material.alpha;
         var value = el("output", {}, Math.round(slider.value * 100) + "%");
         slider.addEventListener("input", function () {
            setAlpha(node, parseFloat(slider.value));
            value.textContent = Math.round(slider.value * 100) + "%";
         });
         alphaLabel.appendChild(slider);
         alphaLabel.appendChild(value);
         props.appendChild(alphaLabel);

         var colorLabel = el("label");
         colorLabel.appendChild(el("span", {}, "Color"));
         var picker = el("input", {type: "color"});
         picker.value = meshes[0].material.diffuseColor.toHexString().toLowerCase();
         picker.addEventListener("input", function () { setColor(node, picker.value); });
         colorLabel.appendChild(picker);
         props.appendChild(colorLabel);
      }

      var buttons = el("div", {"class": "d3d-buttons"});
      function button(text, title, action) {
         var b = el("button", {type: "button", title: title}, text);
         b.addEventListener("click", action);
         buttons.appendChild(b);
      }
      var visible = node.checkbox ? node.checkbox.checked : node.visible;
      button("Focus", "Zoom on this node (F)", function () { focus(node); });
      button(visible ? "Hide" : "Show", "Show / hide (H)", function () { setVisible(node, !visible); });
      button("Isolate", "Show only this node (I)", function () { isolate(node); });
      button("Reset", "Restore the original color and opacity", function () { resetAppearance(node); });
      props.appendChild(buttons);
   }

   // ---------------------------------------------------------------- filter
   function applyFilter() {
      var query = search.value.trim().toLowerCase();
      function mark(node) {
         var childMatch = false;
         node.children.forEach(function (c) { if (mark(c)) childMatch = true; });
         var match = !query || node.name.toLowerCase().indexOf(query) >= 0;
         node.filteredOut = !(match || childMatch);
         if (query && childMatch) node.expanded = true;
         return !node.filteredOut;
      }
      mark(root);
      root.filteredOut = false;
      renderTree();
   }
   search.addEventListener("input", applyFilter);

   // ---------------------------------------------------------------- toolbar
   var toolbar = el("div", {id: "d3d-toolbar"});
   function toolButton(text, title, action, active) {
      var b = el("button", {type: "button", title: title}, text);
      if (active !== undefined) b.classList.toggle("d3d-active", active);
      b.addEventListener("click", function () {
         var state = action();
         if (active !== undefined) b.classList.toggle("d3d-active", state);
      });
      toolbar.appendChild(b);
      return b;
   }
   var treeButton = toolButton("Tree", "Show / hide the scene tree (T)", togglePanel, true);
   toolButton("Fit", "Fit the whole model (F without selection)", function () { focus(root); });
   toolButton("Show all", "Show all nodes (A)", showAll);
   toolbar.appendChild(el("span", {"class": "d3d-sep"}));
   Object.keys(VIEWS).forEach(function (name) {
      toolButton(name, name + " view", function () { setView(VIEWS[name].clone()); });
   });
   toolbar.appendChild(el("span", {"class": "d3d-sep"}));
   var edgesButton = toolButton("Edges", "Show / hide the edges (E)", toggleEdges, true);
   var wireframeButton = toolButton("Wireframe", "Wireframe display (W)", toggleWireframe, false);
   toolButton("Axes", "Show / hide the axes", toggleAxes, true);
   var inspectorButton = toolButton("Inspector", "Babylonjs inspector, for debugging", toggleInspector, false);
   document.body.appendChild(toolbar);
   document.body.appendChild(el("div", {id: "d3d-help"},
      "Click: select · double click: focus · F focus · H hide · I isolate · A show all · Esc deselect"));

   // ---------------------------------------------------------------- picking and keyboard
   function pickedNode(pick) {
      if (!pick || !pick.hit || !pick.pickedMesh) return null;
      return meshToNode.get(pick.pickedMesh.uniqueId) || null;
   }

   scene.onPointerObservable.add(function (info) {
      if (info.event.button !== 0) return;
      var node = pickedNode(info.pickInfo);
      if (info.type === BABYLON.PointerEventTypes.POINTERTAP) {
         select(node);
      } else if (info.type === BABYLON.PointerEventTypes.POINTERDOUBLETAP && node) {
         focus(node);
      }
   }, BABYLON.PointerEventTypes.POINTERTAP | BABYLON.PointerEventTypes.POINTERDOUBLETAP);

   document.addEventListener("keydown", function (e) {
      if (e.target.tagName === "INPUT" || e.ctrlKey || e.metaKey || e.altKey) return;
      var key = e.key.toLowerCase();
      if (key === "escape") select(null);
      else if (key === "f") focus(selected || root);
      else if (key === "h" && selected) setVisible(selected, !(selected.checkbox ? selected.checkbox.checked : selected.visible));
      else if (key === "i" && selected) isolate(selected);
      else if (key === "a") showAll();
      else if (key === "t") treeButton.click();
      else if (key === "e") edgesButton.click();
      else if (key === "w") wireframeButton.click();
      else return;
      e.preventDefault();
   });

   renderTree();
   ctx.engine.resize();
   focus(root);
   if (data.debug) {
      toggleInspector();
      inspectorButton.classList.add("d3d-active");
   }

   return {root: root, nodes: nodes, select: select, setVisible: setVisible, setAlpha: setAlpha,
           setColor: setColor, isolate: isolate, focus: focus, setView: setView};
}
